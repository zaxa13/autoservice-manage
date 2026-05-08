"""Оплата заказа клиентом (наличные / карта / ЮКасса)."""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    YOOKASSA = "yookassa"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Payment(Base, TenantMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        # ЮКасса гарантирует глобальную уникальность payment_id, но per-tenant
        # уникальности нам достаточно для индекса/lookup.
        UniqueConstraint(
            "tenant_id", "yookassa_payment_id",
            name="uq_payments_tenant_yookassa",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="RESTRICT",
            name="fk_payments_order",
        ),
        Index("ix_payments_tenant_order", "tenant_id", "order_id"),
    )
