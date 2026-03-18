from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from app.schemas.customer import Customer


class BrandRef(BaseModel):
    """Ссылка на марку"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID марки")
    name: str = Field(..., description="Название марки")


class ModelRef(BaseModel):
    """Ссылка на модель"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID модели")
    name: str = Field(..., description="Название модели")


class VehicleBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    vin: Optional[str] = Field(None, max_length=17, description="VIN номер (до 17 символов)")
    license_plate: Optional[str] = Field(None, description="Государственный номер")
    brand_id: int = Field(..., description="ID марки автомобиля")
    model_id: int = Field(..., description="ID модели автомобиля")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="Год выпуска")
    mileage: Optional[int] = Field(None, ge=0, description="Пробег в км")
    customer_id: int = Field(..., description="ID клиента-владельца")


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    vin: Optional[str] = Field(None, max_length=17, description="VIN номер")
    license_plate: Optional[str] = Field(None, description="Государственный номер")
    brand_id: Optional[int] = Field(None, description="ID марки")
    model_id: Optional[int] = Field(None, description="ID модели")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="Год выпуска")
    mileage: Optional[int] = Field(None, ge=0, description="Пробег в км")
    customer_id: Optional[int] = Field(None, description="ID клиента-владельца")


class Vehicle(VehicleBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int = Field(..., description="Уникальный ID транспортного средства")
    created_at: datetime = Field(..., description="Дата создания")
    customer: Optional[Customer] = Field(None, description="Данные владельца")
    brand: Optional[BrandRef] = Field(None, description="Марка автомобиля")
    model: Optional[ModelRef] = Field(None, description="Модель автомобиля")
