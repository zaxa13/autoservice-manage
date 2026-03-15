from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AppointmentPostBase(BaseModel):
    name: str
    max_slots: int = 5
    slot_times: Optional[List[str]] = None  # слоты по времени: ["09:00", "11:00", ...]
    color: Optional[str] = None
    sort_order: int = 0


class AppointmentPostCreate(AppointmentPostBase):
    pass


class AppointmentPostUpdate(BaseModel):
    name: Optional[str] = None
    max_slots: Optional[int] = None
    slot_times: Optional[List[str]] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class AppointmentPost(AppointmentPostBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
