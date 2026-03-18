from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="Логин пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    role: UserRole = Field(..., description="Роль пользователя (admin, manager, mechanic, accountant)")


class UserCreate(UserBase):
    password: str = Field(..., min_length=4, description="Пароль (мин. 4 символа)")


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="Новый логин")
    email: Optional[EmailStr] = Field(None, description="Новый email")
    role: Optional[UserRole] = Field(None, description="Новая роль")
    is_active: Optional[bool] = Field(None, description="Активен ли пользователь")
    employee_id: Optional[int] = Field(None, description="ID привязанного сотрудника")
    password: Optional[str] = Field(None, min_length=4, description="Новый пароль")


class UserInDB(UserBase):
    id: int = Field(..., description="Уникальный ID пользователя")
    is_active: bool = Field(..., description="Активен ли пользователь")
    employee_id: Optional[int] = Field(None, description="ID привязанного сотрудника")
    password_must_be_changed: bool = Field(False, description="Требуется смена пароля при входе")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=4, description="Новый пароль (мин. 4 символа)")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email адрес учётной записи")


class ConfirmResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Токен из письма")
    new_password: str = Field(..., min_length=4, description="Новый пароль (мин. 4 символа)")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, description="Новый пароль для пользователя")


class User(UserInDB):
    pass


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access-токен")
    token_type: str = Field(default="bearer", description="Тип токена")
