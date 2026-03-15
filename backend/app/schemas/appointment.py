from pydantic import BaseModel, ConfigDict
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

    id: int
    name: str


class ModelRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AppointmentVehicleInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    license_plate: Optional[str] = None
    brand: Optional[BrandRef] = None
    model: Optional[ModelRef] = None
    year: Optional[int] = None


class OrderRef(BaseModel):
    id: int
    number: str

    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    date: date
    time: time_type
    customer_name: str
    customer_phone: str
    description: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    vehicle_id: Optional[int] = None
    employee_id: Optional[int] = None
    post_id: Optional[int] = None
    order_id: Optional[int] = None
    sort_order: Optional[int] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    date: Optional[date] = None
    time: Optional[time_type] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    vehicle_id: Optional[int] = None
    employee_id: Optional[int] = None
    post_id: Optional[int] = None
    order_id: Optional[int] = None
    sort_order: Optional[int] = None


class Appointment(AppointmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    vehicle: Optional[AppointmentVehicleInfo] = None
    order: Optional[OrderRef] = None

    class Config:
        from_attributes = True
