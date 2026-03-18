from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class CustomerBase(BaseModel):
    full_name: str = Field(..., min_length=1, description="ФИО клиента")
    phone: str = Field(..., min_length=5, description="Номер телефона клиента")
    email: Optional[EmailStr] = Field(None, description="Email клиента")
    address: Optional[str] = Field(None, description="Адрес клиента")
    notes: Optional[str] = Field(None, description="Заметки по клиенту")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, description="ФИО клиента")
    phone: Optional[str] = Field(None, min_length=5, description="Номер телефона")
    email: Optional[EmailStr] = Field(None, description="Email клиента")
    address: Optional[str] = Field(None, description="Адрес клиента")
    notes: Optional[str] = Field(None, description="Заметки по клиенту")


class Customer(CustomerBase):
    id: int = Field(..., description="Уникальный ID клиента")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")

    class Config:
        from_attributes = True
