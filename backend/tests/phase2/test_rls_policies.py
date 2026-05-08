"""RLS metadata: на каждой бизнес-таблице ENABLE+FORCE и `tenant_isolation` policy."""
from __future__ import annotations

import pytest

from app.models import Base


EXPECTED_BUSINESS_TABLES = sorted(
    t.name for t in Base.metadata.sorted_tables
    if t.schema == "app" and t.name != "alembic_version"
)


def _query(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_rls_enabled_and_forced(super_conn, table):
    rows = _query(super_conn, """
        SELECT c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname='app' AND c.relname=%s
    """, (table,))
    assert rows, f"{table}: not found"
    enabled, forced = rows[0]
    assert enabled, f"{table}: RLS not ENABLED"
    assert forced, f"{table}: RLS not FORCED (owner обходил бы политику)"


@pytest.mark.parametrize("table", EXPECTED_BUSINESS_TABLES)
def test_tenant_isolation_policy_exists(super_conn, table):
    rows = _query(super_conn, """
        SELECT polname, polcmd,
               pg_get_expr(polqual, polrelid) AS using_expr,
               pg_get_expr(polwithcheck, polrelid) AS check_expr
        FROM pg_policy
        WHERE polrelid = ('app.' || %s)::regclass
    """, (table,))
    assert rows, f"{table}: нет policy"
    by_name = {r[0]: r for r in rows}
    assert "tenant_isolation" in by_name, f"{table}: нет policy 'tenant_isolation'"

    name, cmd, using, check = by_name["tenant_isolation"]
    # cmd '*' = ALL (PG не различает).
    assert cmd == "*", f"{table}: policy cmd={cmd}, ожидали ALL (*)"
    assert using and "current_tenant" in using, (
        f"{table}: USING={using!r} не ссылается на app.current_tenant()"
    )
    assert check and "current_tenant" in check, (
        f"{table}: WITH CHECK={check!r} не ссылается на app.current_tenant()"
    )


def test_only_one_policy_per_table(super_conn):
    """Не должно быть случайных дополнительных политик."""
    rows = _query(super_conn, """
        SELECT schemaname || '.' || tablename, count(*)
        FROM pg_policies
        WHERE schemaname='app'
        GROUP BY schemaname, tablename
        HAVING count(*) > 1
    """)
    assert not rows, f"Таблицы с >1 policy: {rows}"


def test_app_current_tenant_returns_null_without_setting(super_conn):
    rows = _query(super_conn, "SELECT app.current_tenant()")
    assert rows == [(None,)]


def test_app_current_tenant_returns_uuid_when_set(super_conn):
    super_conn.autocommit = False
    with super_conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute(
            "SET LOCAL app.tenant_id = '11111111-1111-1111-1111-111111111111'"
        )
        cur.execute("SELECT app.current_tenant()")
        val = cur.fetchone()[0]
        cur.execute("COMMIT")
    assert str(val) == "11111111-1111-1111-1111-111111111111"


def test_migrator_role_has_bypassrls(super_conn):
    rows = _query(super_conn, """
        SELECT rolname, rolbypassrls
        FROM pg_roles
        WHERE rolname IN ('migrator_app','migrator_platform','tenant_app','platform_app')
        ORDER BY rolname
    """)
    by_role = dict(rows)
    assert by_role["migrator_app"] is True
    assert by_role["migrator_platform"] is True
    assert by_role["tenant_app"] is False, "tenant_app НЕ должен иметь BYPASSRLS"
    assert by_role["platform_app"] is False
