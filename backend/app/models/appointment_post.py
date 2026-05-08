"""Пост (колонка) на доске записи. Один пост = одна Kanban-колонка."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Integer,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class AppointmentPost(Base, TenantMixin):
    __tablename__ = "appointment_posts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # Слоты по времени, напр. ["09:00", "11:00", "13:00", "15:00", "17:00"].
    # Postgres JSONB — никаких больше TypeDecorator-костылей.
    slot_times: Mapped[list[str] | None] = mapped_column(JSONB)
    color: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)
