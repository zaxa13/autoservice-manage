from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from app.models.work import WorkCategory


class WorkBase(BaseModel):
    name: str = Field(..., min_length=1, description="Название вида работы")
    description: Optional[str] = Field(None, description="Описание работы")
    price: Decimal = Field(..., ge=0, description="Стоимость работы")
    duration_minutes: int = Field(60, ge=1, description="Продолжительность работы в минутах")
    category: WorkCategory = Field(WorkCategory.OTHER, description="Категория работы")


class WorkCreate(WorkBase):
    pass


class WorkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Название вида работы")
    description: Optional[str] = Field(None, description="Описание работы")
    price: Optional[Decimal] = Field(None, ge=0, description="Стоимость работы")
    duration_minutes: Optional[int] = Field(None, ge=1, description="Продолжительность в минутах")
    category: Optional[WorkCategory] = Field(None, description="Категория работы")


class Work(WorkBase):
    id: int = Field(..., description="Уникальный ID вида работы")

    class Config:
        from_attributes = True
