"""Phase 3 fixtures: JWT helpers, FastAPI test client, общие тенант-UUID.

Тесты Фазы 3 покрывают application-слой: JWT-декодер, FastAPI-зависимость
`get_tenant_db`, Celery-декоратор tenant-контекста, онбординг-сид.
Тесты зависят от живой Postgres + PgBouncer (см. tests/phase2/conftest.py).
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Iterator

import psycopg2
import psycopg2.extensions
import pytest
import pytest_asyncio
from jose import jwt

# Тенант-UUID и helper переиспользуем из phase2.
from tests.phase2.conftest import TENANT_ALPHA, TENANT_BETA, tenant_txn  # noqa: F401


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------
def _secret_key() -> str:
    """SECRET_KEY должен быть проставлен в env под тестовый процесс.
    В рантайме его кладёт platform-api при провижининге."""
    val = os.environ.get("SECRET_KEY", "").strip()
    if not val or len(val) < 32:
        pytest.skip("SECRET_KEY (≥32 chars) is required for phase 3 tests")
    return val


def _algorithm() -> str:
    return os.environ.get("ALGORITHM", "HS256")


def make_token(
    *,
    tenant_id: uuid.UUID | None = TENANT_ALPHA,
    owner_id: uuid.UUID | None = None,
    user_id: int | None = None,
    sub: str | None = None,
    roles: list[str] | None = None,
    expires_in: timedelta | None = None,
    extra: dict | None = None,
    secret: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Кодирует JWT в формате, который ожидает tenant-app.

    Минимальный валидный токен — `tenant_id` + `exp`. Остальное опционально.
    """
    payload: dict = {}
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    if owner_id is not None:
        payload["owner_id"] = str(owner_id)
    if user_id is not None:
        payload["user_id"] = user_id
    if sub is not None:
        payload["sub"] = sub
    if roles is not None:
        payload["roles"] = roles
    if expires_in is not None:
        payload["exp"] = datetime.now(timezone.utc) + expires_in
    else:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=15)
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload,
        secret if secret is not None else _secret_key(),
        algorithm=algorithm or _algorithm(),
    )


@pytest.fixture
def secret_key() -> str:
    return _secret_key()


@pytest.fixture
def token_factory():
    """Factory-фикстура: используется как `token_factory(tenant_id=..., expires_in=...)`."""
    return make_token


# ---------------------------------------------------------------------------
# DB connection (повтор логики phase2.conftest для изоляции — fixture scoping
# по subdir в pytest)
# ---------------------------------------------------------------------------
@contextmanager
def _open(url: str) -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(url)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def migrator_conn():
    url = os.environ.get("TEST_PG_MIGRATOR_URL", "").strip()
    if not url:
        pytest.skip("TEST_PG_MIGRATOR_URL is required")
    with _open(url) as c:
        yield c


@pytest.fixture
def super_conn():
    url = os.environ.get("TEST_PG_SUPER_URL", "").strip()
    if not url:
        pytest.skip("TEST_PG_SUPER_URL is required")
    with _open(url) as c:
        yield c


# ---------------------------------------------------------------------------
# DB cleanup (autouse) — те же таблицы что в phase2
# ---------------------------------------------------------------------------
_BUSINESS_TABLES = [
    "cash_transactions", "cash_transaction_categories", "cash_accounts",
    "warehouse_transactions", "warehouse_items", "receipt_lines", "receipt_documents",
    "salaries", "salary_schemes", "payments", "order_parts", "order_works", "orders",
    "appointments", "appointment_posts", "integration_logs", "settings",
    "password_reset_tokens", "users", "vehicles", "vehicle_models", "vehicle_brands",
    "customers", "employees", "suppliers", "parts", "works", "tenant_counters",
]


@pytest.fixture(autouse=True)
def clean_db():
    url = os.environ.get("TEST_PG_MIGRATOR_URL", "").strip()
    if not url:
        yield
        return
    with _open(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE "
                + ", ".join(f"app.{t}" for t in _BUSINESS_TABLES)
                + " RESTART IDENTITY CASCADE"
            )
        conn.commit()
    yield


# ---------------------------------------------------------------------------
# Async DB engine для тестов, дёргающих app-код (get_tenant_db и т.п.).
# Используем тот же URL что и рантайм tenant_app.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _ensure_runtime_database_url():
    """Конфиг tenant-app читает DATABASE_URL — в тестах подкладываем тот же
    URL что и для рантайма (asyncpg, role=tenant_app, через pgbouncer)."""
    url = os.environ.get("TEST_PG_TENANT_ASYNC_URL", "").strip()
    if url:
        os.environ["DATABASE_URL"] = url


# ---------------------------------------------------------------------------
# Helpers для seed данных в тенантах
# ---------------------------------------------------------------------------
@pytest.fixture
def seed_customer(migrator_conn):
    """Фикстура-функция: вставляет customer под migrator (BYPASSRLS)."""
    def _seed(tenant_id: uuid.UUID, name: str = "test", phone: str = "+700") -> int:
        with migrator_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app.customers (tenant_id, full_name, phone) "
                "VALUES (%s, %s, %s) RETURNING id",
                (str(tenant_id), name, phone),
            )
            cust_id = cur.fetchone()[0]
        migrator_conn.commit()
        return cust_id
    return _seed
