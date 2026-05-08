"""Smoke-тест: tenant-app FastAPI поднимается без ошибок и отвечает на /health."""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from .conftest import TENANT_ALPHA, make_token


pytestmark = pytest.mark.asyncio


@pytest.fixture
def app():
    from app.main import app as main_app
    return main_app


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_openapi_renders(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec["paths"]
    # Подключены только мигрированные роуты в Phase 3.
    assert "/health" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/customers/" in paths


async def test_auth_me_returns_claims(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"], user_id=1)
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(TENANT_ALPHA)
    assert body["roles"] == ["admin"]
    assert body["user_id"] == 1


async def test_auth_me_without_token_returns_401(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
