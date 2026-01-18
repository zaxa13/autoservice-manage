from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.models.employee import EmployeePosition
from app.models.user import UserRole


class EmployeeBase(BaseModel):
    full_name: str
    position: EmployeePosition
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    hire_date: date
    salary_base: Decimal


class EmployeeCreate(EmployeeBase):
    # Опциональные поля для создания пользователя
    username: Optional[str] = None
    password: Optional[str] = None
    user_role: Optional[UserRole] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    position: Optional[EmployeePosition] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    salary_base: Optional[Decimal] = None
    is_active: Optional[bool] = None


class Employee(EmployeeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

