"""End-to-end тесты /api/v1/settings/revenue-plan."""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from .conftest import TENANT_ALPHA, TENANT_BETA, make_token

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


async def test_get_unset_returns_null_amount(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/settings/revenue-plan?year=2026&month=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == {"year": 2026, "month": 5, "amount": None}


async def test_set_requires_admin(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.put(
        "/api/v1/settings/revenue-plan",
        json={"year": 2026, "month": 5, "amount": 1000000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_set_and_get(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.put(
        "/api/v1/settings/revenue-plan",
        json={"year": 2026, "month": 5, "amount": 1500000},
        headers=headers,
    )
    assert r.status_code == 200
    r = await client.get(
        "/api/v1/settings/revenue-plan?year=2026&month=5", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["amount"] == 1500000.0


async def test_update_overwrites(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    await client.put(
        "/api/v1/settings/revenue-plan",
        json={"year": 2026, "month": 5, "amount": 1_000_000},
        headers=headers,
    )
    await client.put(
        "/api/v1/settings/revenue-plan",
        json={"year": 2026, "month": 5, "amount": 2_500_000},
        headers=headers,
    )
    r = await client.get(
        "/api/v1/settings/revenue-plan?year=2026&month=5", headers=headers
    )
    assert r.json()["amount"] == 2_500_000.0


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])

    await client.put(
        "/api/v1/settings/revenue-plan",
        json={"year": 2026, "month": 5, "amount": 100},
        headers={"Authorization": f"Bearer {t_a}"},
    )
    # Beta для того же year/month — отдельный план.
    r = await client.get(
        "/api/v1/settings/revenue-plan?year=2026&month=5",
        headers={"Authorization": f"Bearer {t_b}"},
    )
    assert r.status_code == 200
    assert r.json()["amount"] is None
