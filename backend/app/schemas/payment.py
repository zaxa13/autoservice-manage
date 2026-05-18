from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.payment import PaymentMethod, PaymentStatus


class PaymentBase(BaseModel):
    order_id: int = Field(..., description="ID заказ-наряда")
    amount: Decimal = Field(..., gt=0, description="Сумма платежа")
    payment_method: PaymentMethod = Field(..., description="Способ оплаты (cash, card, transfer, yookassa)")


class PaymentCreate(PaymentBase):
    """Создание платежа (наличные/карта/другое)."""


class PaymentYooKassaCreate(BaseModel):
    order_id: int = Field(..., description="ID заказ-наряда")
    amount: Decimal = Field(..., gt=0, description="Сумма платежа")
    return_url: Optional[str] = Field(None, description="URL возврата после оплаты")


class PaymentCancel(BaseModel):
    """Запрос на отмену платежа."""
    amount: Optional[Decimal] = Field(None, gt=0, description="Сумма для частичной отмены (null — отмена полной суммы)")


class Payment(PaymentBase):
    id: int = Field(..., description="Уникальный ID платежа")
    yookassa_payment_id: Optional[str] = Field(None, description="ID платежа в YooKassa")
    status: PaymentStatus = Field(..., description="Статус платежа (pending, succeeded, cancelled)")
    created_at: datetime = Field(..., description="Дата создания")

    class Config:
        from_attributes = True


class PaymentLogEntry(BaseModel):
    """Снимок состояния платежа из app.payment_logs."""
    id: int = Field(..., description="ID записи лога")
    payment_id: int = Field(..., description="ID платежа, к которому относится снимок")
    order_id: int = Field(..., description="ID заказа")
    amount: Decimal = Field(..., description="Сумма платежа на момент снимка")
    payment_method: str = Field(..., description="Способ оплаты")
    status: str = Field(..., description="Статус платежа на момент снимка")
    employee_id: Optional[int] = Field(None, description="ID сотрудника-актора")
    employee_name: Optional[str] = Field(None, description="ФИО сотрудника-актора")
    employee_position: Optional[str] = Field(None, description="Должность сотрудника")
    created_at: datetime = Field(..., description="Когда сделан снимок")

    class Config:
        from_attributes = True
