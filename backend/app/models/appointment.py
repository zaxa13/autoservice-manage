"""Запись клиента на обслуживание."""
import enum
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    WAITING = "waiting"
    ARRIVED = "arrived"
    IN_WORK = "in_work"
    READY = "ready"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class Appointment(Base, TenantMixin):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AppointmentStatus.SCHEDULED.value
    )
    vehicle_id: Mapped[int | None] = mapped_column(BigInteger)
    employee_id: Mapped[int | None] = mapped_column(BigInteger)
    post_id: Mapped[int | None] = mapped_column(BigInteger)
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "vehicle_id"],
            ["vehicles.tenant_id", "vehicles.id"],
            ondelete="SET NULL",
            name="fk_appointments_vehicle",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="SET NULL",
            name="fk_appointments_employee",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "post_id"],
            ["appointment_posts.tenant_id", "appointment_posts.id"],
            ondelete="SET NULL",
            name="fk_appointments_post",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="SET NULL",
            name="fk_appointments_order",
        ),
        Index("ix_appointments_tenant_date", "tenant_id", "date"),
        Index("ix_appointments_tenant_post_date", "tenant_id", "post_id", "date"),
    )
