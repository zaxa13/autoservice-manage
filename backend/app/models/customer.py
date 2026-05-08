"""Клиент автосервиса."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class Customer(Base, TenantMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        Index("ix_customers_tenant_phone", "tenant_id", "phone"),
    )
