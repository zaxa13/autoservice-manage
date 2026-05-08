"""Логи интеграций (ЮКасса, SMS, GIBDD, поставщики)."""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class IntegrationType(str, enum.Enum):
    YOOKASSA = "yookassa"
    SMS = "sms"
    EMAIL = "email"
    PARTS_SUPPLIER = "parts_supplier"
    GIBDD = "gibdd"


class IntegrationLog(Base, TenantMixin):
    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    request_data: Mapped[str | None] = mapped_column(Text)
    response_data: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        Index("ix_integration_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_integration_logs_tenant_type", "tenant_id", "integration_type"),
    )
