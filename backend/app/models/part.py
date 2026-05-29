"""Справочник запчастей."""
import enum
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class PartCategory(str, enum.Enum):
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    SUSPENSION = "suspension"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    BODY = "body"
    CONSUMABLES = "consumables"
    OTHER = "other"


class Part(Base, TenantMixin):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100))
    brand_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("part_brands.id", ondelete="SET NULL"),
        nullable=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    purchase_price_last: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="шт")
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default=PartCategory.OTHER.value
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        Index("ix_parts_tenant_part_number", "tenant_id", "part_number"),
    )
