"""POST /api/v1/auth/login — happy / wrong password / unknown email /
inactive user.

Тесты дёргают полноценный FastAPI app (с подключённым auth-роутером)
через httpx ASGITransport. БД — реальный shared-DB sandbox (см.
phase2.conftest). User'ы заводятся под migrator (BYPASSRLS), чтобы
обойти tenant_id-RLS на app.users.
"""
from __future__ import annotations

import uuid

import httpx
import pytest
import pytest_asyncio
from jose import jwt

from app.core.security import get_password_hash
from app.main import app as fastapi_app

from .conftest import TENANT_ALPHA, TENANT_BETA


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def seed_user(migrator_conn):
    """Inserts a row into app.users under migrator_app (BYPASSRLS).

    Returns the inserted user_id.
    """
    def _seed(
        *,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        username: str | None = None,
        role: str = "admin",
        is_active: bool = True,
    ) -> int:
        with migrator_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app.users "
                "(tenant_id, username, email, password_hash, role, is_active) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    str(tenant_id),
                    username or email.split("@")[0],
                    email,
                    get_password_hash(password),
                    role,
                    is_active,
                ),
            )
            uid = cur.fetchone()[0]
        migrator_conn.commit()
        return uid
    return _seed


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
async def test_login_happy_returns_token_with_tenant_id(client, seed_user, secret_key):
    user_id = seed_user(
        tenant_id=TENANT_ALPHA,
        email="happy@example.com",
        password="s3cret-pw",
        role="admin",
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "happy@example.com", "password": "s3cret-pw"},
    )
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["token_type"] == "bearer"
    token = body["access_token"]

    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    assert payload["tenant_id"] == str(TENANT_ALPHA)
    assert payload["user_id"] == user_id
    assert payload["roles"] == ["admin"]
    assert payload["sub"] == "happy@example.com"
    assert "exp" in payload


async def test_login_returns_token_with_correct_tenant_for_each_user(
    client, seed_user, secret_key
):
    """Два user'а с разными tenant_id → каждый получает токен со своим tenant_id."""
    seed_user(tenant_id=TENANT_ALPHA, email="alpha@example.com", password="pw")
    seed_user(tenant_id=TENANT_BETA, email="beta@example.com", password="pw")

    r_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "alpha@example.com", "password": "pw"},
    )
    r_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "beta@example.com", "password": "pw"},
    )
    assert r_a.status_code == 200
    assert r_b.status_code == 200

    payload_a = jwt.decode(r_a.json()["access_token"], secret_key, algorithms=["HS256"])
    payload_b = jwt.decode(r_b.json()["access_token"], secret_key, algorithms=["HS256"])
    assert payload_a["tenant_id"] == str(TENANT_ALPHA)
    assert payload_b["tenant_id"] == str(TENANT_BETA)


# ---------------------------------------------------------------------------
# Auth failures
# ---------------------------------------------------------------------------
async def test_login_unknown_email_returns_401(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert r.status_code == 401


async def test_login_wrong_password_returns_401(client, seed_user):
    seed_user(tenant_id=TENANT_ALPHA, email="user@example.com", password="correct-pw")

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-pw"},
    )
    assert r.status_code == 401


async def test_login_inactive_user_returns_403(client, seed_user):
    seed_user(
        tenant_id=TENANT_ALPHA,
        email="inactive@example.com",
        password="pw",
        is_active=False,
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "pw"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
async def test_login_invalid_email_format_returns_422(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "pw"},
    )
    assert r.status_code == 422


async def test_login_missing_password_returns_422(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "x@example.com"},
    )
    assert r.status_code == 422
