from pydantic import BaseModel
from typing import Optional
from datetime import date, time, datetime


class AppointmentBase(BaseModel):
    date: date
    time: time
    customer_name: str
    customer_phone: str
    description: Optional[str] = None
    vehicle_id: Optional[int] = None
    employee_id: Optional[int] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    date: Optional[date] = None
    time: Optional[time] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    description: Optional[str] = None
    vehicle_id: Optional[int] = None
    employee_id: Optional[int] = None


class Appointment(AppointmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Опциональные связи - можно добавить позже через lazy loading если нужно
    # vehicle: Optional[Vehicle] = None
    # employee: Optional[Employee] = None

    class Config:
        from_attributes = True
