"""End-to-end тесты /api/v1/employees."""
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


def _payload(name: str = "Иванов И.", position: str = "mechanic") -> dict:
    return {
        "full_name": name,
        "position": position,
        "hire_date": "2026-01-01",
        "salary_base": "50000",
    }


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/employees/")
    assert r.status_code == 401


async def test_create_requires_admin(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.post(
        "/api/v1/employees/", json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_create_and_get(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/employees/", json=_payload("Петров П."),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    eid = r.json()["id"]

    r = await client.get(
        f"/api/v1/employees/{eid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Петров П."


async def test_create_with_user_account(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    payload = _payload("Сидоров С.")
    payload.update({
        "username": "sidorov",
        "password": "pass1234",
        "user_role": "mechanic",
        "email": "sidorov@example.com",
    })
    r = await client.post(
        "/api/v1/employees/", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text

    # users-роут показывает созданного user
    r = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "sidorov" in usernames


async def test_create_with_user_dup_username_returns_400(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    payload1 = _payload("Иванов И.")
    payload1.update({"username": "dup", "password": "p", "user_role": "mechanic", "email": "a@a.com"})
    r = await client.post(
        "/api/v1/employees/", json=payload1,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text

    payload2 = _payload("Петров П.")
    payload2.update({"username": "dup", "password": "p", "user_role": "manager", "email": "b@b.com"})
    r = await client.post(
        "/api/v1/employees/", json=payload2,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.post(
        "/api/v1/employees/", json=_payload("Alpha-emp"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/employees/", json=_payload("Beta-emp"),
        headers={"Authorization": f"Bearer {t_b}"},
    )
    r_a = await client.get(
        "/api/v1/employees/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/employees/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert {e["full_name"] for e in r_a.json()} == {"Alpha-emp"}
    assert {e["full_name"] for e in r_b.json()} == {"Beta-emp"}


async def test_positions_lookup_no_auth(client):
    """Lookup-эндпоинты без auth — справочные."""
    r = await client.get("/api/v1/employees/positions")
    assert r.status_code == 200
    values = {p["value"] for p in r.json()}
    assert values == {"admin", "manager", "mechanic"}


async def test_user_roles_lookup_no_auth(client):
    r = await client.get("/api/v1/employees/user-roles")
    assert r.status_code == 200
    values = {p["value"] for p in r.json()}
    assert values == {"admin", "manager", "mechanic", "accountant"}
