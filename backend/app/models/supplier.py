"""Поставщик запчастей."""
from sqlalchemy import (
    BigInteger,
    Identity,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class Supplier(Base, TenantMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(20))
    kpp: Mapped[str | None] = mapped_column(String(20))
    legal_address: Mapped[str | None] = mapped_column(String(500))
    contact: Mapped[str | None] = mapped_column(String(255))
    bank_name: Mapped[str | None] = mapped_column(String(255))
    bik: Mapped[str | None] = mapped_column(String(20))
    bank_account: Mapped[str | None] = mapped_column(String(50))
    correspondent_account: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)
