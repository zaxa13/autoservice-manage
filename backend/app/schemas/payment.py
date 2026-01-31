from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.payment import PaymentMethod, PaymentStatus


class PaymentBase(BaseModel):
    order_id: int
    amount: Decimal
    payment_method: PaymentMethod


class PaymentCreate(PaymentBase):
    """Создание платежа (наличные/карта/другое)."""


class PaymentYooKassaCreate(BaseModel):
    order_id: int
    amount: Decimal
    return_url: Optional[str] = None


class PaymentCancel(BaseModel):
    """Запрос на отмену платежа."""

    amount: Optional[Decimal] = None  # если None - отмена всей суммы


class Payment(PaymentBase):
    id: int
    yookassa_payment_id: Optional[str] = None
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True

