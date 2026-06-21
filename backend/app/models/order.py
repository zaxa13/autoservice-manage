"""Заказ-наряд: Order + OrderWork (работы) + OrderPart (запчасти).

Номер заказа `Order.number` — UNIQUE per tenant. Генерация — через таблицу
`tenant_counters` (см. миграцию 0001), атомарно через UPDATE...RETURNING.
"""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class OrderStatus(str, enum.Enum):
    NEW = "new"
    ESTIMATION = "estimation"
    IN_PROGRESS = "in_progress"
    READY_FOR_PAYMENT = "ready_for_payment"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base, TenantMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mechanic_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=OrderStatus.NEW.value)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    mileage_at_service: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(2000))
    recommendations: Mapped[str | None] = mapped_column(String(2000))
    comments: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "number", name="uq_orders_tenant_number"),
        ForeignKeyConstraint(
            ["tenant_id", "vehicle_id"],
            ["vehicles.tenant_id", "vehicles.id"],
            ondelete="RESTRICT",
            name="fk_orders_vehicle",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="RESTRICT",
            name="fk_orders_employee",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "mechanic_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="SET NULL",
            name="fk_orders_mechanic",
        ),
        Index("ix_orders_tenant_created", "tenant_id", "created_at"),
        Index("ix_orders_tenant_status", "tenant_id", "status"),
        Index("ix_orders_tenant_vehicle", "tenant_id", "vehicle_id"),
    )


class OrderWork(Base, TenantMixin):
    __tablename__ = "order_works"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    work_id: Mapped[int | None] = mapped_column(BigInteger)
    work_name: Mapped[str | None] = mapped_column(String(255))
    mechanic_id: Mapped[int | None] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="CASCADE",
            name="fk_order_works_order",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "work_id"],
            ["works.tenant_id", "works.id"],
            ondelete="SET NULL",
            name="fk_order_works_work",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "mechanic_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="SET NULL",
            name="fk_order_works_mechanic",
        ),
        Index("ix_order_works_tenant_order", "tenant_id", "order_id"),
    )


class OrderPart(Base, TenantMixin):
    __tablename__ = "order_parts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    part_id: Mapped[int | None] = mapped_column(BigInteger)
    part_name: Mapped[str | None] = mapped_column(String(255))
    article: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="CASCADE",
            name="fk_order_parts_order",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "part_id"],
            ["parts.tenant_id", "parts.id"],
            ondelete="SET NULL",
            name="fk_order_parts_part",
        ),
        Index("ix_order_parts_tenant_order", "tenant_id", "order_id"),
    )
