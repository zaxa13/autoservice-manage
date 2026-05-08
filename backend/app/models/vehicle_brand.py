"""Справочники марок и моделей автомобилей. Per-tenant: при онбординге
тенанта системные дефолты копируются в его строки.
"""
from sqlalchemy import (
    BigInteger,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class VehicleBrand(Base, TenantMixin):
    __tablename__ = "vehicle_brands"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "name", name="uq_vehicle_brands_tenant_name"),
    )


class VehicleModel(Base, TenantMixin):
    __tablename__ = "vehicle_models"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    brand_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "brand_id"],
            ["vehicle_brands.tenant_id", "vehicle_brands.id"],
            ondelete="CASCADE",
            name="fk_vehicle_models_brand",
        ),
        UniqueConstraint(
            "tenant_id", "brand_id", "name",
            name="uq_vehicle_models_tenant_brand_name",
        ),
        Index("ix_vehicle_models_tenant_brand", "tenant_id", "brand_id"),
    )
