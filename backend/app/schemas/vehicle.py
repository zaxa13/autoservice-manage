from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.customer import Customer


class BrandRef(BaseModel):
    """Ссылка на марку"""
    id: int
    name: str

    class Config:
        from_attributes = True


class ModelRef(BaseModel):
    """Ссылка на модель"""
    id: int
    name: str

    class Config:
        from_attributes = True


class VehicleBase(BaseModel):
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    brand_id: int
    model_id: int
    year: Optional[int] = None
    mileage: Optional[int] = None  # Пробег в км
    customer_id: int


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    customer_id: Optional[int] = None


class Vehicle(VehicleBase):
    id: int
    created_at: datetime
    customer: Optional[Customer] = None
    brand: Optional[BrandRef] = None
    model: Optional[ModelRef] = None

    class Config:
        from_attributes = True
