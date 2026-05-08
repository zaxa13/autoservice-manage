"""Справочник работ (услуг)."""
import enum
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Identity,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class WorkCategory(str, enum.Enum):
    DIAGNOSTICS = "diagnostics"
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    SUSPENSION = "suspension"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    COOLING = "cooling"
    FUEL_SYSTEM = "fuel_system"
    EXHAUST = "exhaust"
    CLIMATE = "climate"
    MAINTENANCE = "maintenance"
    BODY_WORK = "body_work"
    PAINTING = "painting"
    TIRE_SERVICE = "tire_service"
    GLASS = "glass"
    REPAIR = "repair"
    OTHER = "other"


class Work(Base, TenantMixin):
    __tablename__ = "works"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default=WorkCategory.OTHER.value
    )

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)
