"""End-to-end тесты /api/v1/works."""
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


def _payload(name: str = "Замена масла", price: float = 1500.0) -> dict:
    return {"name": name, "price": price, "duration_minutes": 30, "category": "engine"}


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/works/")
    assert r.status_code == 401


async def test_create_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.post(
        "/api/v1/works/", json=_payload(), headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_create_and_get(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/works/", json=_payload(), headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201, r.text
    work_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/works/{work_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "Замена масла"


async def test_search_by_name(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    await client.post(
        "/api/v1/works/",
        json=_payload("Замена масла"),
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/works/",
        json=_payload("Замена тормозных колодок"),
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get(
        "/api/v1/works/?search=масла", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    names = [w["name"] for w in r.json()]
    assert names == ["Замена масла"]


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post(
        "/api/v1/works/", json=_payload("Alpha-work"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/works/", json=_payload("Beta-work"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get("/api/v1/works/", headers={"Authorization": f"Bearer {t_a}"})
    r_b = await client.get("/api/v1/works/", headers={"Authorization": f"Bearer {t_b}"})
    assert {w["name"] for w in r_a.json()} == {"Alpha-work"}
    assert {w["name"] for w in r_b.json()} == {"Beta-work"}


async def test_update_partial(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.post(
        "/api/v1/works/",
        json=_payload("Old", 1000),
        headers={"Authorization": f"Bearer {token}"},
    )
    work_id = r.json()["id"]
    r2 = await client.put(
        f"/api/v1/works/{work_id}",
        json={"price": "2000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["name"] == "Old"
    assert float(body["price"]) == 2000.0


async def test_get_nonexistent_returns_404(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/works/999999", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 404
