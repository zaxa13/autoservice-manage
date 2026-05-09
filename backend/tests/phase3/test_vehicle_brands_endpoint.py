"""End-to-end тесты /api/v1/vehicle-brands."""
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


_IMPORT_PAYLOAD = {
    "brands": [
        {"name": "Toyota", "models": ["Camry", "Corolla", "RAV4"]},
        {"name": "BMW", "models": ["X5", "M3"]},
    ]
}


async def test_import_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.post(
        "/api/v1/vehicle-brands/import",
        json=_IMPORT_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_import_creates_brands_and_models(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/vehicle-brands/import",
        json=_IMPORT_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["brands_count"] == 2

    # GET / возвращает список (отсортированный по name)
    r = await client.get(
        "/api/v1/vehicle-brands/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    names = [b["name"] for b in r.json()["brands"]]
    assert names == ["BMW", "Toyota"]


async def test_models_by_brand_id(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    await client.post(
        "/api/v1/vehicle-brands/import",
        json=_IMPORT_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get(
        "/api/v1/vehicle-brands/", headers={"Authorization": f"Bearer {token}"}
    )
    toyota_id = next(b["id"] for b in r.json()["brands"] if b["name"] == "Toyota")
    r = await client.post(
        "/api/v1/vehicle-brands/models",
        json={"brand_id": toyota_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert {m["name"] for m in r.json()["models"]} == {"Camry", "Corolla", "RAV4"}


async def test_models_request_without_brand_returns_400(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/vehicle-brands/models",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])

    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Alpha-brand", "models": ["m"]}]},
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Beta-brand", "models": ["m"]}]},
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get(
        "/api/v1/vehicle-brands/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/vehicle-brands/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert [b["name"] for b in r_a.json()["brands"]] == ["Alpha-brand"]
    assert [b["name"] for b in r_b.json()["brands"]] == ["Beta-brand"]
