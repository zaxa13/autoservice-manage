"""End-to-end тесты /api/v1/appointment-posts."""
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


def _payload(name: str = "Пост 1", **kw) -> dict:
    base = {"name": name, "max_slots": 5, "sort_order": 0}
    base.update(kw)
    return base


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/appointment-posts/")
    assert r.status_code == 401


async def test_full_lifecycle(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # CREATE с slot_times (JSONB)
    r = await client.post(
        "/api/v1/appointment-posts/",
        json=_payload(slot_times=["09:00", "11:00", "14:00"], color="#ff0000"),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["slot_times"] == ["09:00", "11:00", "14:00"]
    assert r.json()["color"] == "#ff0000"

    # UPDATE
    r = await client.put(
        f"/api/v1/appointment-posts/{pid}",
        json={"max_slots": 10, "color": "#00ff00"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["max_slots"] == 10
    assert r.json()["color"] == "#00ff00"

    # DELETE
    r = await client.delete(f"/api/v1/appointment-posts/{pid}", headers=headers)
    assert r.status_code == 204

    # GET → 404
    r = await client.get(f"/api/v1/appointment-posts/{pid}", headers=headers)
    assert r.status_code == 404


async def test_list_sorted_by_sort_order(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/appointment-posts/", json=_payload("C", sort_order=2), headers=headers)
    await client.post("/api/v1/appointment-posts/", json=_payload("A", sort_order=0), headers=headers)
    await client.post("/api/v1/appointment-posts/", json=_payload("B", sort_order=1), headers=headers)
    r = await client.get("/api/v1/appointment-posts/", headers=headers)
    assert [p["name"] for p in r.json()] == ["A", "B", "C"]


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post(
        "/api/v1/appointment-posts/",
        json=_payload("Alpha-post"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/appointment-posts/",
        json=_payload("Beta-post"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get(
        "/api/v1/appointment-posts/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/appointment-posts/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert [p["name"] for p in r_a.json()] == ["Alpha-post"]
    assert [p["name"] for p in r_b.json()] == ["Beta-post"]
