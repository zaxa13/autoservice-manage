"""End-to-end тесты /api/v1/suppliers."""
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


def _payload(name: str = "Поставщик 1", inn: str = "7700000000") -> dict:
    return {"name": name, "inn": inn}


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/suppliers/")
    assert r.status_code == 401


async def test_full_lifecycle(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # CREATE
    r = await client.post("/api/v1/suppliers/", json=_payload(), headers=headers)
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    # GET
    r = await client.get(f"/api/v1/suppliers/{sid}", headers=headers)
    assert r.status_code == 200

    # UPDATE
    r = await client.put(
        f"/api/v1/suppliers/{sid}",
        json={"contact": "Иванов И.И., +7-900-000-0000"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["contact"].startswith("Иванов")

    # DELETE
    r = await client.delete(f"/api/v1/suppliers/{sid}", headers=headers)
    assert r.status_code == 204

    # GET after delete → 404
    r = await client.get(f"/api/v1/suppliers/{sid}", headers=headers)
    assert r.status_code == 404


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post(
        "/api/v1/suppliers/", json=_payload("Alpha-sup"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/suppliers/", json=_payload("Beta-sup"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get(
        "/api/v1/suppliers/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/suppliers/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert {s["name"] for s in r_a.json()} == {"Alpha-sup"}
    assert {s["name"] for s in r_b.json()} == {"Beta-sup"}


async def test_delete_other_tenant_returns_404(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    r = await client.post(
        "/api/v1/suppliers/", json=_payload("Beta-only"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    sid = r.json()["id"]
    r = await client.delete(
        f"/api/v1/suppliers/{sid}",
        headers={"Authorization": f"Bearer {t_a}"},
    )
    assert r.status_code == 404
