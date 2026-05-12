"""Пользователь tenant-приложения (admin / manager / mechanic / accountant)."""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MECHANIC = "mechanic"
    ACCOUNTANT = "accountant"


class User(Base, TenantMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.MECHANIC.value)
    employee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    password_must_be_changed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        # Username уникален внутри тенанта (логины типа "admin", "manager"
        # могут пересекаться между разными tenant'ами).
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        # Email — глобально уникальный. Используется как identity для login
        # на app.auto-works.pro (см. функцию `app.lookup_user_for_login`):
        # форма принимает email+password, без tenant_id, поэтому пара
        # (email, tenant) была бы неоднозначной.
        UniqueConstraint("email", name="uq_users_email_global"),
        # Один user максимум на одного employee внутри тенанта.
        UniqueConstraint("tenant_id", "employee_id", name="uq_users_tenant_employee"),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="SET NULL",
            name="fk_users_employee",
        ),
    )
