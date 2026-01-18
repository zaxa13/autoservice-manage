from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from app.models.work import WorkCategory


class WorkBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    duration_minutes: int = 60
    category: WorkCategory = WorkCategory.OTHER


class WorkCreate(WorkBase):
    pass


class WorkUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    duration_minutes: Optional[int] = None
    category: Optional[WorkCategory] = None


class Work(WorkBase):
    id: int

    class Config:
        from_attributes = True

