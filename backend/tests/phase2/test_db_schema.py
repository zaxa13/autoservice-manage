"""DB introspection: схема `app` соответствует моделям после `alembic upgrade`.

Это не дубль `test_python_models.py` — там мы проверяем что _модели_
правильные, тут что _физическая БД_ правильная.
"""
from __future__ import annotations

import pytest

from app.models import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EXPECTED_BUSINESS_TABLES = sorted(
    t.name for t in Base.metadata.sorted_tables
    if t.schema == "app" and t.name != "alembic_version"
)


def _query(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Schema-level
# ---------------------------------------------------------------------------
def test_schema_app_exists(super_conn):
    rows = _query(super_conn, "SELECT 1 FROM pg_namespace WHERE nspname='app'")
    assert rows == [(1,)]


def test_helper_function_current_tenant_exists(super_conn):
    rows = _query(super_conn, """
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname='app' AND p.proname='current_tenant'
    """)
    assert rows == [(1,)]


def test_business_tables_match_models(super_conn):
    rows = _query(super_conn, """
        SELECT tablename FROM pg_tables
        WHERE schemaname='app' AND tablename != 'alembic_version'
        ORDER BY tablename
    """)
    actual = sorted(r[0] for r in rows)
    assert actual == EXPECTED_BUSINESS_TABLES


# ---------------------------------------------------------------------------
# Per-table guarantees
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_table_has_tenant_id_uuid_not_null(super_conn, table):
    rows = _query(super_conn, """
        SELECT data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema='app' AND table_name=%s AND column_name='tenant_id'
    """, (table,))
    assert rows, f"{table}: no tenant_id column"
    data_type, is_nullable = rows[0]
    assert data_type == "uuid", f"{table}.tenant_id is {data_type}, expected uuid"
    assert is_nullable == "NO", f"{table}.tenant_id must be NOT NULL"


@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_pk_starts_with_tenant_id(super_conn, table):
    rows = _query(super_conn, """
        SELECT a.attname
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE con.contype='p' AND n.nspname='app' AND c.relname=%s
        ORDER BY k.ord
    """, (table,))
    pk_cols = [r[0] for r in rows]
    assert pk_cols, f"{table}: no PK"
    assert pk_cols[0] == "tenant_id", f"{table}: PK is {pk_cols}, must start with tenant_id"
    assert len(pk_cols) >= 2, f"{table}: PK is single-column {pk_cols}"


@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_all_fks_are_composite_with_tenant_id(super_conn, table):
    rows = _query(super_conn, """
        SELECT con.conname,
               array_agg(a.attname ORDER BY k.ord) AS local_cols
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE con.contype='f' AND n.nspname='app' AND c.relname=%s
        GROUP BY con.conname
    """, (table,))
    bad = [
        (name, cols)
        for name, cols in rows
        if cols[0] != "tenant_id" or len(cols) < 2
    ]
    assert not bad, f"{table}: некомпозитные/без tenant_id FK: {bad}"


@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_all_unique_constraints_start_with_tenant_id(super_conn, table):
    rows = _query(super_conn, """
        SELECT con.conname,
               array_agg(a.attname ORDER BY k.ord) AS cols
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE con.contype='u' AND n.nspname='app' AND c.relname=%s
        GROUP BY con.conname
    """, (table,))
    bad = [(name, cols) for name, cols in rows if cols[0] != "tenant_id"]
    assert not bad, f"{table}: UNIQUE без tenant_id первым: {bad}"


# ---------------------------------------------------------------------------
# DEFAULT PRIVILEGES автоматически выдаются на новые таблицы
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_tenant_app_has_dml_grants_on_each_table(super_conn, table):
    rows = _query(super_conn, """
        SELECT privilege_type FROM information_schema.role_table_grants
        WHERE table_schema='app' AND table_name=%s AND grantee='tenant_app'
    """, (table,))
    privs = sorted(r[0] for r in rows)
    expected = sorted(["SELECT", "INSERT", "UPDATE", "DELETE"])
    assert privs == expected, (
        f"{table}: tenant_app имеет {privs}, ожидали {expected} "
        "(см. ALTER DEFAULT PRIVILEGES в bootstrap)"
    )


# ---------------------------------------------------------------------------
# Identity columns корректно сгенерированы
# ---------------------------------------------------------------------------
def test_orders_id_is_identity(super_conn):
    rows = _query(super_conn, """
        SELECT identity_generation
        FROM information_schema.columns
        WHERE table_schema='app' AND table_name='orders' AND column_name='id'
    """)
    assert rows and rows[0][0] in ("ALWAYS", "BY DEFAULT"), rows


def test_settings_pk_is_tenant_id_key(super_conn):
    """settings — единственная таблица с натуральным PK (tenant_id, key)."""
    rows = _query(super_conn, """
        SELECT a.attname
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE con.contype='p' AND n.nspname='app' AND c.relname='settings'
        ORDER BY k.ord
    """)
    assert [r[0] for r in rows] == ["tenant_id", "key"]
