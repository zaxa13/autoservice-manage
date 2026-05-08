"""Declarative Base + TenantMixin для shared-DB архитектуры.

Все таблицы tenant-приложения живут в схеме `app`. Метаданные настроены
с дефолтным `schema="app"`, поэтому в `__table_args__` отдельно schema
указывать не нужно.

Каждая бизнес-таблица:
    - наследует Base и TenantMixin (даёт колонку tenant_id UUID NOT NULL);
    - имеет составной первичный ключ `(tenant_id, id)` или `(tenant_id, key)`;
    - все составные индексы и UNIQUE начинаются с tenant_id;
    - все FK на другие тенант-таблицы — составные `(tenant_id, parent_id)`.

RLS-политики добавляются в Alembic-миграции, не в моделях.
"""
import uuid

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


metadata = MetaData(schema="app")


class Base(DeclarativeBase):
    metadata = metadata


class TenantMixin:
    """Колонка tenant_id UUID NOT NULL.

    Не задаёт PK — конкретная таблица оформляет PrimaryKeyConstraint
    в `__table_args__`, обычно `("tenant_id", "id")`.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
