"""Сотрудник автосервиса."""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Identity,
    Numeric,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class EmployeePosition(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MECHANIC = "mechanic"


class Employee(Base, TenantMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    salary_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)
