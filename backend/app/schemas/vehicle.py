from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.customer import Customer


class VehicleBase(BaseModel):
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    brand: str
    model: str
    year: Optional[int] = None
    customer_id: int


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    customer_id: Optional[int] = None


class Vehicle(VehicleBase):
    id: int
    created_at: datetime
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True

