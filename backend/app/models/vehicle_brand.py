"""Глобальный справочник марок и моделей автомобилей.

Общий для всех тенантов: одна запись на марку/модель, RLS отсутствует,
наполняется миграцией 0003 из brands_filtered.json. tenant-app имеет
только SELECT.
"""
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base


class VehicleBrand(Base):
    __tablename__ = "vehicle_brands"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )


class VehicleModel(Base):
    __tablename__ = "vehicle_models"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    brand_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicle_brands.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_vehicle_models_brand_name"),
        Index("ix_vehicle_models_brand", "brand_id"),
    )
