"""Per-tenant key-value настройки."""
from sqlalchemy import PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class Setting(Base, TenantMixin):
    __tablename__ = "settings"

    # Естественный ключ — без синтетического id.
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(String(2000))

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "key"),)
