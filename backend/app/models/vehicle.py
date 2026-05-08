"""Транспортное средство."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class Vehicle(Base, TenantMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(50))
    license_plate: Mapped[str | None] = mapped_column(String(20))
    brand_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    model_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    mileage: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        # VIN уникален в рамках тенанта (если задан).
        UniqueConstraint("tenant_id", "vin", name="uq_vehicles_tenant_vin"),
        ForeignKeyConstraint(
            ["tenant_id", "brand_id"],
            ["vehicle_brands.tenant_id", "vehicle_brands.id"],
            ondelete="RESTRICT",
            name="fk_vehicles_brand",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "model_id"],
            ["vehicle_models.tenant_id", "vehicle_models.id"],
            ondelete="RESTRICT",
            name="fk_vehicles_model",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            ondelete="RESTRICT",
            name="fk_vehicles_customer",
        ),
        Index("ix_vehicles_tenant_license_plate", "tenant_id", "license_plate"),
        Index("ix_vehicles_tenant_customer", "tenant_id", "customer_id"),
    )
