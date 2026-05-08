"""TDD: FastAPI-зависимость `get_tenant_db`.

Контракт:
- Без Authorization header → 401.
- С невалидным/просроченным токеном → 401.
- С валидным токеном → даёт `AsyncSession` с уже установленным
  `app.tenant_id` и активной транзакцией.
- Внутри запроса видим только данные из своего тенанта (RLS работает
  через зависимость).
- Между запросами контекст не утекает (transaction-pool безопасен).
- Если endpoint бросает — транзакция откатывается.
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import TENANT_ALPHA, TENANT_BETA, make_token


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test app: тонкий FastAPI вокруг get_tenant_db
# ---------------------------------------------------------------------------
@pytest.fixture
def app():
    """Создаёт FastAPI с одним тестовым endpoint, использующим get_tenant_db."""
    from app.dependencies import get_tenant_db  # noqa: PLC0415

    app = FastAPI()

    @app.get("/customers/count")
    async def count_customers(db: AsyncSession = Depends(get_tenant_db)):
        result = await db.execute(text("SELECT count(*) FROM app.customers"))
        return {"count": result.scalar()}

    @app.get("/whoami")
    async def whoami(db: AsyncSession = Depends(get_tenant_db)):
        result = await db.execute(text("SELECT app.current_tenant()"))
        return {"tenant_id": str(result.scalar())}

    @app.get("/insert-and-fail")
    async def insert_and_fail(db: AsyncSession = Depends(get_tenant_db)):
        await db.execute(
            text("INSERT INTO app.customers (tenant_id, full_name, phone) "
                 "VALUES (app.current_tenant(), 'will-rollback', '+700')")
        )
        raise HTTPException(status_code=500, detail="boom")

    @app.get("/insert-and-ok")
    async def insert_and_ok(db: AsyncSession = Depends(get_tenant_db)):
        await db.execute(
            text("INSERT INTO app.customers (tenant_id, full_name, phone) "
                 "VALUES (app.current_tenant(), 'committed', '+700')")
        )
        return {"ok": True}

    return app


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Auth failures → 401
# ---------------------------------------------------------------------------
async def test_no_authorization_header_returns_401(client):
    r = await client.get("/customers/count")
    assert r.status_code == 401


async def test_malformed_authorization_header_returns_401(client):
    r = await client.get(
        "/customers/count", headers={"Authorization": "Basic abc"}
    )
    assert r.status_code == 401


async def test_invalid_jwt_returns_401(client):
    r = await client.get(
        "/customers/count", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert r.status_code == 401


async def test_expired_jwt_returns_401(client):
    token = make_token(
        tenant_id=TENANT_ALPHA, expires_in=timedelta(seconds=-30)
    )
    r = await client.get(
        "/customers/count", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


async def test_jwt_without_tenant_id_returns_401(client):
    token = make_token(tenant_id=None, owner_id=uuid.uuid4())
    r = await client.get(
        "/customers/count", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth success: tenant_id ставится из токена
# ---------------------------------------------------------------------------
async def test_valid_token_sets_tenant_context(client):
    token = make_token(tenant_id=TENANT_ALPHA)
    r = await client.get(
        "/whoami", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["tenant_id"] == str(TENANT_ALPHA)


async def test_isolation_between_tenants(client, seed_customer):
    seed_customer(TENANT_ALPHA, "alpha-1")
    seed_customer(TENANT_ALPHA, "alpha-2")
    seed_customer(TENANT_BETA, "beta-1")

    token_alpha = make_token(tenant_id=TENANT_ALPHA)
    token_beta = make_token(tenant_id=TENANT_BETA)

    r_a = await client.get(
        "/customers/count", headers={"Authorization": f"Bearer {token_alpha}"}
    )
    r_b = await client.get(
        "/customers/count", headers={"Authorization": f"Bearer {token_beta}"}
    )

    assert r_a.status_code == 200 and r_a.json()["count"] == 2
    assert r_b.status_code == 200 and r_b.json()["count"] == 1


# ---------------------------------------------------------------------------
# Transaction semantics
# ---------------------------------------------------------------------------
async def test_endpoint_exception_rolls_back_transaction(client, migrator_conn):
    token = make_token(tenant_id=TENANT_ALPHA)
    r = await client.get(
        "/insert-and-fail", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 500

    with migrator_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 0


async def test_endpoint_success_commits_transaction(client, migrator_conn):
    token = make_token(tenant_id=TENANT_ALPHA)
    r = await client.get(
        "/insert-and-ok", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200

    with migrator_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Cross-request isolation
# ---------------------------------------------------------------------------
async def test_consecutive_requests_different_tenants_dont_leak(client, seed_customer):
    seed_customer(TENANT_ALPHA, "alpha")
    seed_customer(TENANT_BETA, "beta-1")
    seed_customer(TENANT_BETA, "beta-2")
    seed_customer(TENANT_BETA, "beta-3")

    token_a = make_token(tenant_id=TENANT_ALPHA)
    token_b = make_token(tenant_id=TENANT_BETA)

    # Несколько чередующихся запросов: проверяем, что server-side connection
    # из transaction-pool не несёт SET LOCAL предыдущей транзакции.
    for _ in range(3):
        r_a = await client.get(
            "/customers/count", headers={"Authorization": f"Bearer {token_a}"}
        )
        r_b = await client.get(
            "/customers/count", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert r_a.json()["count"] == 1
        assert r_b.json()["count"] == 3
