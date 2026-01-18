from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus
from app.schemas.vehicle import Vehicle
from app.schemas.employee import Employee
from app.schemas.work import Work
from app.schemas.part import Part


class OrderWorkBase(BaseModel):
    work_id: Optional[int] = None  # Nullable для ручного ввода
    work_name: Optional[str] = None  # Название работы при ручном вводе
    quantity: int = 1
    price: Decimal
    discount: Optional[Decimal] = 0  # Скидка в процентах


class OrderWorkCreate(OrderWorkBase):
    pass


class OrderWork(OrderWorkBase):
    id: int
    order_id: int
    total: Decimal
    work: Optional[Work] = None  # Optional, так как может быть ручной ввод

    class Config:
        from_attributes = True


class OrderPartBase(BaseModel):
    part_id: Optional[int] = None  # Nullable для ручного ввода
    part_name: Optional[str] = None  # Название запчасти при ручном вводе
    article: Optional[str] = None  # Артикул запчасти
    quantity: int = 1
    price: Decimal
    discount: Optional[Decimal] = 0  # Скидка в процентах


class OrderPartCreate(OrderPartBase):
    pass


class OrderPart(OrderPartBase):
    id: int
    order_id: int
    total: Decimal
    part: Optional[Part] = None  # Optional, так как может быть ручной ввод

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    vehicle_id: int
    mechanic_id: Optional[int] = None


class OrderCreate(OrderBase):
    recommendations: Optional[str] = None  # Рекомендации
    comments: Optional[str] = None  # Комментарии
    order_works: List[OrderWorkCreate] = []
    order_parts: List[OrderPartCreate] = []


class OrderUpdate(BaseModel):
    mechanic_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    paid_amount: Optional[Decimal] = None  # Сумма оплаты
    recommendations: Optional[str] = None  # Рекомендации
    comments: Optional[str] = None  # Комментарии
    order_works: Optional[List[OrderWorkCreate]] = None
    order_parts: Optional[List[OrderPartCreate]] = None


class Order(OrderBase):
    id: int
    number: str
    employee_id: int
    status: OrderStatus
    total_amount: Decimal
    paid_amount: Decimal
    # recommendations и comments убраны из базовой схемы - они только в OrderDetail
    created_at: datetime
    completed_at: Optional[datetime] = None
    # Опциональные relationships для отображения в списке (загружаются через joinedload)
    vehicle: Optional[Vehicle] = None
    mechanic: Optional[Employee] = None

    class Config:
        from_attributes = True


class OrderDetail(Order):
    vehicle: Vehicle  # Переопределяем как обязательное (в Order оно опциональное)
    employee: Employee
    mechanic: Optional[Employee] = None  # Переопределяем явно
    order_works: List[OrderWork] = []
    order_parts: List[OrderPart] = []
    recommendations: Optional[str] = None  # Рекомендации - только в детальной информации
    comments: Optional[str] = None  # Комментарии - только в детальной информации

    class Config:
        from_attributes = True

