"""tenant_counters: атомарная per-tenant генерация номеров.

Используется для `orders.number`, `receipt_documents.number` и т.п.
Шаблон: INSERT ON CONFLICT DO NOTHING + UPDATE...RETURNING.
"""
from __future__ import annotations

import uuid

from .conftest import TENANT_ALPHA, TENANT_BETA, tenant_txn


def _next(cur, counter_name: str) -> int:
    """Атомарный инкремент. Если строки нет — создаёт её с нуля."""
    cur.execute(
        "INSERT INTO app.tenant_counters (tenant_id, counter_name, value) "
        "VALUES (app.current_tenant(), %s, 0) "
        "ON CONFLICT (tenant_id, counter_name) DO NOTHING",
        (counter_name,),
    )
    cur.execute(
        "UPDATE app.tenant_counters SET value = value + 1 "
        "WHERE tenant_id = app.current_tenant() AND counter_name = %s "
        "RETURNING value",
        (counter_name,),
    )
    return cur.fetchone()[0]


def test_first_call_returns_one(tenant_conn):
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        assert _next(cur, "orders") == 1


def test_consecutive_calls_increment(tenant_conn):
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        assert _next(cur, "orders") == 1
        assert _next(cur, "orders") == 2
        assert _next(cur, "orders") == 3


def test_counters_are_per_tenant(tenant_conn):
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        assert _next(cur, "orders") == 1
        assert _next(cur, "orders") == 2
    with tenant_txn(tenant_conn, TENANT_BETA) as cur:
        # Beta стартует с нуля независимо.
        assert _next(cur, "orders") == 1


def test_counters_are_per_name(tenant_conn):
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        assert _next(cur, "orders") == 1
        assert _next(cur, "orders") == 2
        assert _next(cur, "receipts") == 1
        assert _next(cur, "orders") == 3
