"""End-to-end тесты /api/v1/users."""
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


async def _seed_user_via_employee(client, token, **extra) -> int:
    payload = {
        "full_name": "Test",
        "position": "mechanic",
        "hire_date": "2026-01-01",
        "salary_base": "50000",
        "username": extra.get("username", "testuser"),
        "password": "pass1234",
        "user_role": extra.get("user_role", "mechanic"),
        "email": extra.get("email", "test@example.com"),
    }
    r = await client.post(
        "/api/v1/employees/", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    # Получаем user_id через GET /users
    r = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    return next(u["id"] for u in r.json() if u["username"] == payload["username"])


async def test_list_requires_admin(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_list_users(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    await _seed_user_via_employee(client, token, username="u1", email="u1@a.com")
    r = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert any(u["username"] == "u1" for u in r.json())


async def test_update_user(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    uid = await _seed_user_via_employee(client, token, username="u2", email="u2@a.com")
    r = await client.put(
        f"/api/v1/users/{uid}",
        json={"role": "manager", "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "manager"
    assert body["is_active"] is False


async def test_reset_password_sets_must_change_flag(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    uid = await _seed_user_via_employee(client, token, username="u3", email="u3@a.com")
    r = await client.post(
        f"/api/v1/users/{uid}/reset-password",
        json={"new_password": "newpass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    r = await client.get(
        f"/api/v1/users/{uid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.json()["password_must_be_changed"] is True


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await _seed_user_via_employee(client, t_a, username="alpha-u", email="alpha@a.com")
    r = await client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert r.status_code == 200
    assert all(u["username"] != "alpha-u" for u in r.json())


async def test_get_other_tenant_user_returns_404(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    uid = await _seed_user_via_employee(client, t_a, username="hidden", email="h@a.com")
    r = await client.get(
        f"/api/v1/users/{uid}", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert r.status_code == 404
