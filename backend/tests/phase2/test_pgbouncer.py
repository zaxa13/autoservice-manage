"""PgBouncer transaction-pool: SET LOCAL не утекает между транзакциями.

Это критичный инвариант: pgbouncer переиспользует server-side connection
между разными client-side транзакциями. Если бы мы использовали `SET`
вместо `SET LOCAL`, или поставили GUC вне транзакции — следующий запрос
другого тенанта читал бы под чужим контекстом.
"""
from __future__ import annotations

import uuid

import psycopg2
import pytest

from .conftest import TENANT_ALPHA, TENANT_BETA, tenant_txn


def _seed(migrator_conn, tenant_id: uuid.UUID, n: int) -> None:
    with migrator_conn.cursor() as cur:
        for i in range(n):
            cur.execute(
                "INSERT INTO app.customers (tenant_id, full_name, phone) "
                "VALUES (%s, %s, %s)",
                (str(tenant_id), f"{tenant_id}-{i}", "+700"),
            )
    migrator_conn.commit()


def test_set_local_is_reset_after_commit(tenant_conn):
    """После COMMIT в той же сессии current_tenant() = NULL."""
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute("SELECT app.current_tenant()")
        assert str(cur.fetchone()[0]) == str(TENANT_ALPHA)

    # Без новой транзакции и без SET — должен быть NULL.
    with tenant_conn.cursor() as cur:
        cur.execute("SELECT app.current_tenant()")
        assert cur.fetchone()[0] is None


def test_set_local_is_reset_after_rollback(tenant_conn):
    tenant_conn.autocommit = False
    with tenant_conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL app.tenant_id = %s", (str(TENANT_ALPHA),))
        cur.execute("SELECT app.current_tenant()")
        assert str(cur.fetchone()[0]) == str(TENANT_ALPHA)
        tenant_conn.rollback()

    with tenant_conn.cursor() as cur:
        cur.execute("SELECT app.current_tenant()")
        assert cur.fetchone()[0] is None


def test_two_consecutive_transactions_dont_leak(tenant_conn, migrator_conn):
    """Alpha→Beta в одной клиентской сессии. Pgbouncer может отдать тот же
    server-side connection — но SET LOCAL изолирует."""
    _seed(migrator_conn, TENANT_ALPHA, 2)
    _seed(migrator_conn, TENANT_BETA, 5)

    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 2

    with tenant_txn(tenant_conn, TENANT_BETA) as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 5

    # Возвращаемся к Alpha — снова видим 2.
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 2


def test_separate_sessions_independent(tenant_url, migrator_conn):
    """Две разные клиентские сессии — типичный сценарий: два разных HTTP-запроса.
    Каждая ставит свой SET LOCAL и видит свои данные, друг другу не мешают."""
    _seed(migrator_conn, TENANT_ALPHA, 3)
    _seed(migrator_conn, TENANT_BETA, 7)

    conn_a = psycopg2.connect(tenant_url)
    conn_b = psycopg2.connect(tenant_url)
    try:
        with tenant_txn(conn_a, TENANT_ALPHA) as cur:
            cur.execute("SELECT count(*) FROM app.customers")
            assert cur.fetchone()[0] == 3
        with tenant_txn(conn_b, TENANT_BETA) as cur:
            cur.execute("SELECT count(*) FROM app.customers")
            assert cur.fetchone()[0] == 7
    finally:
        conn_a.close()
        conn_b.close()


def test_pool_mode_is_transaction(super_conn, tenant_url):
    """Контракт: tenant_app ходит ТОЛЬКО через transaction-pool.
    Если из URL извлекается порт 6432 и dbname autoworks_tx — это он."""
    assert "6432" in tenant_url, "tenant_url должен идти через PgBouncer (порт 6432)"
    assert "autoworks_tx" in tenant_url, (
        "tenant_url должен использовать transaction-pool 'autoworks_tx'"
    )
