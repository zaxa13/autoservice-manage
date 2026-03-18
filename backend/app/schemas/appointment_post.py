from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AppointmentPostBase(BaseModel):
    name: str = Field(..., min_length=1, description="Название поста (колонки)")
    max_slots: int = Field(5, ge=1, description="Максимум записей в колонке")
    slot_times: Optional[List[str]] = Field(None, description="Временные слоты (например ['09:00', '11:00', '14:00'])")
    color: Optional[str] = Field(None, description="Цвет поста для отображения в UI")
    sort_order: int = Field(0, description="Порядок сортировки")


class AppointmentPostCreate(AppointmentPostBase):
    pass


class AppointmentPostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Название поста")
    max_slots: Optional[int] = Field(None, ge=1, description="Максимум записей")
    slot_times: Optional[List[str]] = Field(None, description="Временные слоты")
    color: Optional[str] = Field(None, description="Цвет поста")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки")


class AppointmentPost(AppointmentPostBase):
    id: int = Field(..., description="Уникальный ID поста")
    created_at: datetime = Field(..., description="Дата создания")

    class Config:
        from_attributes = True
