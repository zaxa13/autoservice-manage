"""End-to-end тесты /api/v1/appointments."""
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


def _payload(**kw) -> dict:
    base = {
        "date": "2026-06-15",
        "time": "10:00:00",
        "customer_name": "Иван Иванов",
        "customer_phone": "+79991234567",
        "status": "scheduled",
    }
    base.update(kw)
    return base


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/appointments/")
    assert r.status_code == 401


async def test_create_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.post(
        "/api/v1/appointments/", json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_create_minimal_appointment(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/appointments/", json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["customer_name"] == "Иван Иванов"
    assert a["status"] == "scheduled"


async def test_create_with_unknown_vehicle_returns_404(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/appointments/",
        json=_payload(vehicle_id=99999),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_create_with_post_id(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/appointment-posts/",
        json={"name": "Пост 1", "max_slots": 5, "sort_order": 0},
        headers=headers,
    )
    post_id = r.json()["id"]

    r = await client.post(
        "/api/v1/appointments/", json=_payload(post_id=post_id),
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["post_id"] == post_id


async def test_filter_by_date(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/appointments/", json=_payload(date="2026-06-15"), headers=headers
    )
    await client.post(
        "/api/v1/appointments/", json=_payload(date="2026-06-16"), headers=headers
    )
    r = await client.get("/api/v1/appointments/?date=2026-06-15", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_update_status(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/appointments/", json=_payload(), headers=headers)
    aid = r.json()["id"]
    r = await client.put(
        f"/api/v1/appointments/{aid}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


async def test_delete(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/appointments/", json=_payload(), headers=headers)
    aid = r.json()["id"]
    r = await client.delete(f"/api/v1/appointments/{aid}", headers=headers)
    assert r.status_code == 204
    r = await client.get(f"/api/v1/appointments/{aid}", headers=headers)
    assert r.status_code == 404


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post(
        "/api/v1/appointments/", json=_payload(customer_name="Alpha"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/appointments/", json=_payload(customer_name="Beta"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get(
        "/api/v1/appointments/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/appointments/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert {a["customer_name"] for a in r_a.json()} == {"Alpha"}
    assert {a["customer_name"] for a in r_b.json()} == {"Beta"}
