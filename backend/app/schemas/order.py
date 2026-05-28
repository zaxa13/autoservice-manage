from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus
from app.schemas.vehicle import Vehicle
from app.schemas.employee import Employee
from app.schemas.work import Work
from app.schemas.part import Part


def _normalize_article(v: Optional[str]) -> Optional[str]:
    """Обрезка пробелов по краям, верхний регистр, удаление всех пробелов внутри."""
    if v is None:
        return None
    s = v.strip().upper().replace(" ", "")
    return s if s else None


def _normalize_ref_id(v: Optional[int]) -> Optional[int]:
    """0/отрицательный id из фронта → None (запись считается ручной)."""
    return v if (v is not None and v > 0) else None


class OrderWorkBase(BaseModel):
    work_id: Optional[int] = Field(None, description="ID работы из справочника (null для ручного ввода)")
    work_name: Optional[str] = Field(None, description="Название работы при ручном вводе")
    mechanic_id: Optional[int] = Field(None, description="ID механика, выполняющего данную работу")
    quantity: int = Field(1, ge=1, description="Количество")
    price: Decimal = Field(..., ge=0, description="Цена за единицу")
    discount: Optional[Decimal] = Field(0, ge=0, le=100, description="Скидка в процентах")

    @field_validator("work_id", "mechanic_id", mode="before")
    @classmethod
    def _coerce_zero_to_none(cls, v):
        return _normalize_ref_id(v) if isinstance(v, int) else v

    @field_validator("work_name", mode="before")
    @classmethod
    def _strip_work_name(cls, v):
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v

    @model_validator(mode="after")
    def _require_reference_or_name(self):
        if self.work_id is None and not self.work_name:
            raise ValueError(
                "Заполните название работы или выберите её из справочника"
            )
        return self


class OrderWorkCreate(OrderWorkBase):
    pass


class OrderWork(OrderWorkBase):
    id: int = Field(..., description="ID позиции работы")
    order_id: int = Field(..., description="ID заказ-наряда")
    total: Decimal = Field(..., description="Итого с учётом скидки")
    work: Optional[Work] = Field(None, description="Данные работы из справочника")
    mechanic: Optional[Employee] = Field(None, description="Механик, выполняющий работу")

    class Config:
        from_attributes = True


class OrderPartBase(BaseModel):
    part_id: Optional[int] = Field(None, description="ID запчасти из справочника (null для ручного ввода)")
    part_name: Optional[str] = Field(None, description="Название запчасти при ручном вводе")
    article: Optional[str] = Field(None, description="Артикул (нормализуется: верхний регистр, без пробелов)")
    quantity: int = Field(1, ge=1, description="Количество")
    price: Decimal = Field(..., ge=0, description="Цена за единицу")
    discount: Optional[Decimal] = Field(0, ge=0, le=100, description="Скидка в процентах")

    @field_validator("part_id", mode="before")
    @classmethod
    def _coerce_zero_to_none(cls, v):
        return _normalize_ref_id(v) if isinstance(v, int) else v

    @field_validator("article")
    @classmethod
    def normalize_article(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_article(v)

    @field_validator("part_name", mode="before")
    @classmethod
    def _strip_part_name(cls, v):
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v

    @model_validator(mode="after")
    def _require_reference_or_article(self):
        # Если запчасть не из справочника — нужен артикул (и желательно название).
        if self.part_id is None and not self.article:
            raise ValueError(
                "Заполните артикул запчасти или выберите её из справочника"
            )
        return self


class OrderPartCreate(OrderPartBase):
    pass


class OrderPart(OrderPartBase):
    id: int = Field(..., description="ID позиции запчасти")
    order_id: int = Field(..., description="ID заказ-наряда")
    total: Decimal = Field(..., description="Итого с учётом скидки")
    part: Optional[Part] = Field(None, description="Данные запчасти из справочника")

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    vehicle_id: int = Field(..., description="ID транспортного средства")
    mechanic_id: Optional[int] = Field(None, description="ID механика")


class OrderCreate(OrderBase):
    recommendations: Optional[str] = Field(None, description="Рекомендации по обслуживанию")
    comments: Optional[str] = Field(None, description="Комментарии к заказу")
    order_works: List[OrderWorkCreate] = Field(default_factory=list, description="Список работ")
    order_parts: List[OrderPartCreate] = Field(default_factory=list, description="Список запчастей")


class OrderUpdate(BaseModel):
    employee_id: Optional[int] = Field(None, description="ID ответственного менеджера")
    mechanic_id: Optional[int] = Field(None, description="ID механика")
    status: Optional[OrderStatus] = Field(None, description="Статус заказ-наряда")
    paid_amount: Optional[Decimal] = Field(None, ge=0, description="Сумма оплаты")
    recommendations: Optional[str] = Field(None, description="Рекомендации по обслуживанию")
    comments: Optional[str] = Field(None, description="Комментарии к заказу")
    order_works: Optional[List[OrderWorkCreate]] = Field(None, description="Обновлённый список работ")
    order_parts: Optional[List[OrderPartCreate]] = Field(None, description="Обновлённый список запчастей")


class Order(OrderBase):
    id: int = Field(..., description="Уникальный ID заказ-наряда")
    number: str = Field(..., description="Номер заказ-наряда (например ЗН-001)")
    employee_id: int = Field(..., description="ID ответственного сотрудника")
    status: OrderStatus = Field(..., description="Статус заказ-наряда")
    total_amount: Decimal = Field(..., description="Общая сумма заказа")
    paid_amount: Decimal = Field(..., description="Оплаченная сумма")
    created_at: datetime = Field(..., description="Дата создания")
    completed_at: Optional[datetime] = Field(None, description="Дата завершения")
    vehicle: Optional[Vehicle] = Field(None, description="Данные транспортного средства")
    mechanic: Optional[Employee] = Field(None, description="Данные механика")

    class Config:
        from_attributes = True


class OrderDetail(Order):
    vehicle: Optional[Vehicle] = Field(None, description="Данные транспортного средства")
    employee: Optional[Employee] = Field(None, description="Данные ответственного сотрудника")
    mechanic: Optional[Employee] = Field(None, description="Данные механика")
    order_works: List[OrderWork] = Field(default_factory=list, description="Список работ")
    order_parts: List[OrderPart] = Field(default_factory=list, description="Список запчастей")


class OrderListResponse(BaseModel):
    """Пагинированный ответ для списка заказов."""
    items: List[Order] = Field(..., description="Заказы текущей страницы")
    total: int = Field(..., description="Общее количество заказов с учётом фильтров")
    recommendations: Optional[str] = Field(None, description="Рекомендации по обслуживанию")
    comments: Optional[str] = Field(None, description="Комментарии к заказу")

    class Config:
        from_attributes = True

