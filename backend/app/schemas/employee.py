from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.models.employee import EmployeePosition
from app.models.user import UserRole


class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=1, description="ФИО сотрудника")
    position: EmployeePosition = Field(..., description="Должность (admin, manager, mechanic)")
    phone: Optional[str] = Field(None, description="Номер телефона")
    email: Optional[EmailStr] = Field(None, description="Email сотрудника")
    hire_date: date = Field(..., description="Дата приёма на работу")
    salary_base: Decimal = Field(..., ge=0, description="Базовая ставка зарплаты")


class EmployeeCreate(EmployeeBase):
    username: Optional[str] = Field(None, description="Логин для создания учётной записи")
    password: Optional[str] = Field(None, description="Пароль для создания учётной записи")
    user_role: Optional[UserRole] = Field(None, description="Роль пользователя для создания учётной записи")


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, description="ФИО сотрудника")
    position: Optional[EmployeePosition] = Field(None, description="Должность")
    phone: Optional[str] = Field(None, description="Номер телефона")
    email: Optional[EmailStr] = Field(None, description="Email сотрудника")
    salary_base: Optional[Decimal] = Field(None, ge=0, description="Базовая ставка зарплаты")
    is_active: Optional[bool] = Field(None, description="Активен ли сотрудник")


class Employee(EmployeeBase):
    id: int = Field(..., description="Уникальный ID сотрудника")
    is_active: bool = Field(..., description="Активен ли сотрудник")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")

    class Config:
        from_attributes = True
