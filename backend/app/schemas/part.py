from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from app.models.part import PartCategory


class PartBase(BaseModel):
    name: str
    part_number: Optional[str] = None
    brand: Optional[str] = None
    price: Decimal
    unit: str = "шт"
    category: PartCategory = PartCategory.OTHER


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: Optional[str] = None
    part_number: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    category: Optional[PartCategory] = None


class Part(PartBase):
    id: int

    class Config:
        from_attributes = True

