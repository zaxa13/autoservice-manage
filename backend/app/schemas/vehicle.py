from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.customer import Customer


class BrandRef(BaseModel):
    """Ссылка на марку"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str


class ModelRef(BaseModel):
    """Ссылка на модель"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str


class VehicleBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
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
    model_config = ConfigDict(protected_namespaces=())
    
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    customer_id: Optional[int] = None


class Vehicle(VehicleBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    created_at: datetime
    customer: Optional[Customer] = None
    brand: Optional[BrandRef] = None
    model: Optional[ModelRef] = None
