"""End-to-end тесты для /api/v1/customers — эталонный CRUD-роутер."""
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


# Базовый payload для CustomerCreate.
def _customer_payload(name: str = "Тест", phone: str = "+79000000001") -> dict:
    return {"full_name": name, "phone": phone}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/customers/")
    assert r.status_code == 401


async def test_create_without_role_returns_403(client):
    # Токен без admin/manager в roles.
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.post(
        "/api/v1/customers/",
        json=_customer_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
async def test_create_and_get_customer(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Иван Иванов", "+79001234567"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    customer = r.json()
    assert customer["full_name"] == "Иван Иванов"
    assert customer["id"] >= 1

    # GET by id
    r2 = await client.get(
        f"/api/v1/customers/{customer['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["full_name"] == "Иван Иванов"


async def test_list_returns_only_own_tenant_customers(client):
    token_alpha = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    token_beta = make_token(tenant_id=TENANT_BETA, roles=["admin"])

    await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Alpha-1"),
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Alpha-2", "+79000000002"),
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Beta-1"),
        headers={"Authorization": f"Bearer {token_beta}"},
    )

    r_a = await client.get(
        "/api/v1/customers/",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    r_b = await client.get(
        "/api/v1/customers/",
        headers={"Authorization": f"Bearer {token_beta}"},
    )

    assert r_a.status_code == 200 and len(r_a.json()) == 2
    assert r_b.status_code == 200 and len(r_b.json()) == 1
    assert {c["full_name"] for c in r_a.json()} == {"Alpha-1", "Alpha-2"}
    assert r_b.json()[0]["full_name"] == "Beta-1"


async def test_get_other_tenant_customer_returns_404(client):
    token_alpha = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    token_beta = make_token(tenant_id=TENANT_BETA, roles=["admin"])

    r = await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Beta-secret"),
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    beta_id = r.json()["id"]

    # Alpha-токен — должен получить 404 на чужого
    r_a = await client.get(
        f"/api/v1/customers/{beta_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert r_a.status_code == 404


async def test_update_customer(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["manager"])
    r = await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Old name"),
        headers={"Authorization": f"Bearer {token}"},
    )
    customer_id = r.json()["id"]

    r2 = await client.put(
        f"/api/v1/customers/{customer_id}",
        json={"full_name": "New name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["full_name"] == "New name"
    # phone остался прежним (exclude_unset)
    assert r2.json()["phone"] == "+79000000001"


async def test_update_other_tenant_customer_returns_404(client):
    token_alpha = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    token_beta = make_token(tenant_id=TENANT_BETA, roles=["admin"])

    r = await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Beta-x"),
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    beta_id = r.json()["id"]

    r_a = await client.put(
        f"/api/v1/customers/{beta_id}",
        json={"full_name": "hacked"},
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert r_a.status_code == 404


async def test_get_nonexistent_customer_returns_404(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/customers/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_search_by_phone(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    await client.post(
        "/api/v1/customers/",
        json=_customer_payload("Найдись", "+79991234567"),
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get(
        "/api/v1/customers/search/by-phone?phone=999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["full_name"] == "Найдись"
