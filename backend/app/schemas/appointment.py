from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, time as time_type, datetime
from enum import Enum


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    WAITING = "waiting"
    ARRIVED = "arrived"
    IN_WORK = "in_work"
    READY = "ready"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class BrandRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID марки")
    name: str = Field(..., description="Название марки")


class ModelRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID модели")
    name: str = Field(..., description="Название модели")


class AppointmentVehicleInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int = Field(..., description="ID транспортного средства")
    license_plate: Optional[str] = Field(None, description="Государственный номер")
    brand: Optional[BrandRef] = Field(None, description="Марка")
    model: Optional[ModelRef] = Field(None, description="Модель")
    year: Optional[int] = Field(None, description="Год выпуска")


class OrderRef(BaseModel):
    id: int = Field(..., description="ID заказ-наряда")
    number: str = Field(..., description="Номер заказ-наряда")

    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    date: date  # Дата записи (Field(...) not used: Pydantic 2.5 bug with shadowed type names)
    time: time_type = Field(..., description="Время записи")
    customer_name: str = Field(..., min_length=1, description="Имя клиента")
    customer_phone: str = Field(..., min_length=5, description="Телефон клиента")
    description: Optional[str] = Field(None, description="Описание причины визита")
    status: AppointmentStatus = Field(AppointmentStatus.SCHEDULED, description="Статус записи")
    vehicle_id: Optional[int] = Field(None, description="ID транспортного средства")
    employee_id: Optional[int] = Field(None, description="ID ответственного сотрудника")
    post_id: Optional[int] = Field(None, description="ID поста (колонки)")
    order_id: Optional[int] = Field(None, description="ID связанного заказ-наряда")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки внутри поста")


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    date: Optional[date] = None
    time: Optional[time_type] = Field(None, description="Время записи")
    customer_name: Optional[str] = Field(None, min_length=1, description="Имя клиента")
    customer_phone: Optional[str] = Field(None, description="Телефон клиента")
    description: Optional[str] = Field(None, description="Описание причины визита")
    status: Optional[AppointmentStatus] = Field(None, description="Статус записи")
    vehicle_id: Optional[int] = Field(None, description="ID транспортного средства")
    employee_id: Optional[int] = Field(None, description="ID ответственного сотрудника")
    post_id: Optional[int] = Field(None, description="ID поста (колонки)")
    order_id: Optional[int] = Field(None, description="ID связанного заказ-наряда")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки внутри поста")


class Appointment(AppointmentBase):
    id: int = Field(..., description="Уникальный ID записи")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")
    vehicle: Optional[AppointmentVehicleInfo] = Field(None, description="Данные транспортного средства")
    order: Optional[OrderRef] = Field(None, description="Связанный заказ-наряд")

    class Config:
        from_attributes = True
