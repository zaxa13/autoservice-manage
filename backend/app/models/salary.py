"""Зарплата: схема расчёта (per employee) + ведомость за период."""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
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


class SalaryStatus(str, enum.Enum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    PAID = "paid"


class SalaryScheme(Base, TenantMixin):
    __tablename__ = "salary_schemes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    works_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    revenue_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    # Если True — бонус менеджера считается по ВСЕМ закрытым заказам периода
    # (без фильтра по employee_id). Нужно для маленьких автосервисов, где
    # заказы могут закрывать админ/коллеги, но бонус всё равно идёт смене.
    revenue_all_orders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "employee_id", name="uq_salary_schemes_tenant_employee"),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="CASCADE",
            name="fk_salary_schemes_employee",
        ),
    )


class Salary(Base, TenantMixin):
    __tablename__ = "salaries"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    bonus: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    penalty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SalaryStatus.DRAFT.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="RESTRICT",
            name="fk_salaries_employee",
        ),
        Index("ix_salaries_tenant_employee_period", "tenant_id", "employee_id", "period_start"),
    )
