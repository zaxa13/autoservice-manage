"""Глобальный справочник брендов запчастей.

Общий для всех тенантов, как vehicle_brands. RLS нет, наполняется
миграцией 0010. tenant_app имеет только SELECT.
"""
from sqlalchemy import BigInteger, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base


class PartBrand(Base):
    __tablename__ = "part_brands"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
