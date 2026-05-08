"""Static compliance: SQLAlchemy-модели соответствуют контракту shared-DB.

Цель — поймать ошибки до того как они попадут в DB-миграцию: каждая
бизнес-таблица должна нести `tenant_id`, иметь composite PK и индексы
с `tenant_id` первым. Без этого RLS работает, но запросы будут делать
seq scan по таблице со всеми тенантами.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.models._base import TenantMixin
from app.models import Base


# Все таблицы, кроме alembic_version (его создаёт alembic, не наши модели).
ALL_TABLES = [
    t for t in Base.metadata.sorted_tables
    if t.schema == "app" and t.name != "alembic_version"
]


def _table_name(t: sa.Table) -> str:
    return f"{t.schema}.{t.name}"


# ---------------------------------------------------------------------------
# Базовая регистрация
# ---------------------------------------------------------------------------
def test_metadata_default_schema_is_app():
    assert Base.metadata.schema == "app"


def test_at_least_28_business_tables_registered():
    # Если число изменится — тест надо обновить осознанно.
    assert len(ALL_TABLES) >= 28, [t.name for t in ALL_TABLES]


# ---------------------------------------------------------------------------
# tenant_id column
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_table_has_tenant_id_column(table: sa.Table):
    assert "tenant_id" in table.c, f"{_table_name(table)}: no tenant_id column"


@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_tenant_id_is_uuid_not_null(table: sa.Table):
    col = table.c.tenant_id
    assert isinstance(col.type, sa.dialects.postgresql.UUID), (
        f"{_table_name(table)}.tenant_id is {col.type!r}, expected UUID"
    )
    assert col.nullable is False, f"{_table_name(table)}.tenant_id must be NOT NULL"


# ---------------------------------------------------------------------------
# Composite PK
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_pk_starts_with_tenant_id(table: sa.Table):
    pk_cols = [c.name for c in table.primary_key.columns]
    assert pk_cols, f"{_table_name(table)}: no primary key"
    assert pk_cols[0] == "tenant_id", (
        f"{_table_name(table)}: PK is {pk_cols}, must start with tenant_id"
    )
    assert len(pk_cols) >= 2, (
        f"{_table_name(table)}: PK has only {pk_cols} — must be composite"
    )


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_all_multi_column_indexes_start_with_tenant_id(table: sa.Table):
    bad = []
    for ix in table.indexes:
        cols = [c.name for c in ix.columns]
        if len(cols) >= 2 and cols[0] != "tenant_id":
            bad.append((ix.name, cols))
    assert not bad, (
        f"{_table_name(table)}: индексы без tenant_id первым: {bad}"
    )


# ---------------------------------------------------------------------------
# UNIQUE constraints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_all_unique_constraints_start_with_tenant_id(table: sa.Table):
    bad = []
    for uc in table.constraints:
        if isinstance(uc, sa.UniqueConstraint):
            cols = [c.name for c in uc.columns]
            if cols and cols[0] != "tenant_id":
                bad.append((uc.name, cols))
    assert not bad, (
        f"{_table_name(table)}: UNIQUE без tenant_id первым: {bad} — "
        "это даст глобальную уникальность вместо tenant-scoped"
    )


# ---------------------------------------------------------------------------
# Foreign keys: должны быть составными и начинаться с tenant_id.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", ALL_TABLES, ids=_table_name)
def test_all_foreign_keys_are_composite_with_tenant_id(table: sa.Table):
    bad = []
    for fk in table.foreign_key_constraints:
        local_cols = [c.name for c in fk.columns]
        if "tenant_id" not in local_cols:
            bad.append((fk.name, local_cols, "no tenant_id"))
            continue
        if local_cols[0] != "tenant_id":
            bad.append((fk.name, local_cols, "tenant_id not first"))
            continue
        if len(local_cols) < 2:
            bad.append((fk.name, local_cols, "single-column FK"))
    assert not bad, (
        f"{_table_name(table)}: FK не композитные / без tenant_id: {bad}"
    )


# ---------------------------------------------------------------------------
# TenantMixin — проверяем, что миксин использован (а не просто колонка скопирована)
# ---------------------------------------------------------------------------
def test_all_mapped_classes_use_tenant_mixin():
    """Все классы моделей наследуют TenantMixin — это контракт, через который
    мы централизованно поддерживаем tenant_id."""
    bad: list[str] = []
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        # alembic_version не маппится через нас, фильтр по нашим Base-классам
        if not issubclass(cls, Base):
            continue
        if not issubclass(cls, TenantMixin):
            bad.append(cls.__name__)
    assert not bad, f"Классы без TenantMixin: {bad}"
