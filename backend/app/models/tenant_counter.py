"""Per-tenant счётчики для номеров заказов, накладных и т.п.

Использование:

    UPDATE app.tenant_counters
       SET value = value + 1
     WHERE tenant_id = :tid AND counter_name = :name
    RETURNING value;

Атомарно: блокировка строки + инкремент в одной транзакции. Если строки
нет — INSERT (`ON CONFLICT DO NOTHING`) + повтор UPDATE.
"""
from sqlalchemy import BigInteger, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class TenantCounter(Base, TenantMixin):
    __tablename__ = "tenant_counters"

    counter_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "counter_name"),)
