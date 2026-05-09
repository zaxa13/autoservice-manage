"""End-to-end тесты /api/v1/parts."""
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


def _payload(name: str = "Фильтр", part_number: str = "FIL-001", price: float = 500.0) -> dict:
    return {
        "name": name,
        "part_number": part_number,
        "price": price,
        "category": "consumables",
    }


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/parts/")
    assert r.status_code == 401


async def test_create_normalizes_part_number(client):
    """Артикул нормализуется в верхний регистр без пробелов (см. schemas/part.py)."""
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/parts/",
        json=_payload(part_number="abc 123 xyz"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["part_number"] == "ABC123XYZ"


async def test_get_returns_stock_quantity_zero_when_no_warehouse_item(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/parts/", json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    pid = r.json()["id"]

    r = await client.get(
        f"/api/v1/parts/{pid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["stock_quantity"] == 0


async def test_search_by_part_number(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/parts/", json=_payload(part_number="OEM-AAA-001"), headers=headers)
    await client.post("/api/v1/parts/", json=_payload(part_number="OEM-BBB-002"), headers=headers)
    r = await client.get("/api/v1/parts/?search=AAA", headers=headers)
    assert r.status_code == 200
    nums = [p["part_number"] for p in r.json()]
    assert nums == ["OEM-AAA-001"]


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post("/api/v1/parts/", json=_payload("Alpha-part", "AAA-001"),
                      headers={"Authorization": f"Bearer {t_a}"})
    await client.post("/api/v1/parts/", json=_payload("Beta-part", "BBB-001"),
                      headers={"Authorization": f"Bearer {t_b}"})
    r_a = await client.get("/api/v1/parts/", headers={"Authorization": f"Bearer {t_a}"})
    r_b = await client.get("/api/v1/parts/", headers={"Authorization": f"Bearer {t_b}"})
    assert {p["name"] for p in r_a.json()} == {"Alpha-part"}
    assert {p["name"] for p in r_b.json()} == {"Beta-part"}


async def test_update_part(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.post(
        "/api/v1/parts/", json=_payload(price=100),
        headers={"Authorization": f"Bearer {token}"},
    )
    pid = r.json()["id"]
    r = await client.put(
        f"/api/v1/parts/{pid}",
        json={"price": "200"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert float(r.json()["price"]) == 200.0
