"""Фикстуры для Phase 2 acceptance-тестов.

Принципы:
- Тесты идут против реального Postgres + PgBouncer (sandbox из Фазы 1).
- Используем psycopg2 (sync) — проще писать тесты и читать assertions,
  чем гонять asyncpg/event loop под каждый запрос.
- Три connection-URL передаются через env vars; пустые → skip.
- `clean_db` перед каждым тестом обнуляет бизнес-таблицы под ролью
  migrator (BYPASSRLS) — гарантирует независимость тестов.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extensions
import pytest

# ---------------------------------------------------------------------------
# Test tenants
# ---------------------------------------------------------------------------
TENANT_ALPHA = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_BETA = uuid.UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# Connection URL fixtures (session-scoped)
# ---------------------------------------------------------------------------
def _env_url(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        pytest.skip(
            f"{name} not set — see backend/tests/README.md for required env vars"
        )
    return val


@pytest.fixture(scope="session")
def super_url() -> str:
    return _env_url("TEST_PG_SUPER_URL")


@pytest.fixture(scope="session")
def migrator_url() -> str:
    return _env_url("TEST_PG_MIGRATOR_URL")


@pytest.fixture(scope="session")
def tenant_url() -> str:
    return _env_url("TEST_PG_TENANT_URL")


# ---------------------------------------------------------------------------
# Connection fixtures
# ---------------------------------------------------------------------------
@contextmanager
def _open(url: str) -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(url)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def super_conn(super_url):
    """Ad-hoc connection под суперюзером — для introspection (pg_class etc.)."""
    with _open(super_url) as c:
        yield c


@pytest.fixture
def migrator_conn(migrator_url):
    """Connection под migrator_app (BYPASSRLS) — для setup данных в нескольких тенантах."""
    with _open(migrator_url) as c:
        yield c


@pytest.fixture
def tenant_conn(tenant_url):
    """Connection под tenant_app через PgBouncer transaction-pool — то, как
    ходит рантайм. RLS активна; перед запросами нужен `SET LOCAL`."""
    with _open(tenant_url) as c:
        yield c


# ---------------------------------------------------------------------------
# Cleanup fixture (function-scoped, autouse)
# ---------------------------------------------------------------------------
# Бизнес-таблицы в порядке от child→parent — даём CASCADE для надёжности.
_BUSINESS_TABLES = [
    "cash_transactions",
    "cash_transaction_categories",
    "cash_accounts",
    "warehouse_transactions",
    "warehouse_items",
    "receipt_lines",
    "receipt_documents",
    "salaries",
    "salary_schemes",
    "payments",
    "order_parts",
    "order_works",
    "orders",
    "appointments",
    "appointment_posts",
    "integration_logs",
    "settings",
    "password_reset_tokens",
    "users",
    "vehicles",
    "vehicle_models",
    "vehicle_brands",
    "customers",
    "employees",
    "suppliers",
    "parts",
    "works",
    "tenant_counters",
]


@pytest.fixture(autouse=True)
def clean_db(migrator_url):
    """Truncate all business tables before each test under migrator role."""
    with _open(migrator_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE "
                + ", ".join(f"app.{t}" for t in _BUSINESS_TABLES)
                + " RESTART IDENTITY CASCADE"
            )
        conn.commit()
    yield


# ---------------------------------------------------------------------------
# Helper: установить tenant_id внутри транзакции (имитация рантайм-middleware)
# ---------------------------------------------------------------------------
@contextmanager
def tenant_txn(conn, tenant_id: uuid.UUID):
    """Открывает транзакцию с уже установленным `app.tenant_id`."""
    if conn.autocommit:
        conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL app.tenant_id = %s", (str(tenant_id),))
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
