"""End-to-end тесты ручных платежей по заказу + /vehicles/{id}/history."""
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


async def _setup_with_order(client, tenant=TENANT_ALPHA, order_amount: int = 5000) -> dict:
    bare = make_token(tenant_id=tenant, roles=["admin"])
    bare_h = {"Authorization": f"Bearer {bare}"}

    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "Manager", "position": "manager",
            "hire_date": "2026-01-01", "salary_base": "50000",
        },
        headers=bare_h,
    )
    eid = r.json()["id"]
    full = make_token(tenant_id=tenant, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}

    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Owner", "phone": "+7900"}, headers=headers,
    )
    cust = r.json()["id"]
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Toyota", "models": ["Camry"]}]},
        headers=headers,
    )
    bid = (await client.get("/api/v1/vehicle-brands/", headers=headers)).json()["brands"][0]["id"]
    mid = (await client.post(
        "/api/v1/vehicle-brands/models", json={"brand_id": bid}, headers=headers
    )).json()["models"][0]["id"]
    r = await client.post(
        "/api/v1/vehicles/",
        json={
            "customer_id": cust, "brand_id": bid, "model_id": mid,
            "license_plate": "А001АА", "year": 2020,
        },
        headers=headers,
    )
    vid = r.json()["id"]

    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": vid,
            "order_works": [{"work_name": "Замена масла", "quantity": 1, "price": str(order_amount), "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    oid = r.json()["id"]

    return {"headers": headers, "vehicle_id": vid, "order_id": oid, "amount": order_amount}


async def _seed_onboarding(headers):
    """Вызывает seed_tenant_defaults для добавления категории «Оплата заказа»."""
    from app.database import tenant_session
    from app.services import tenant_onboarding
    from app.core.security import decode_tenant_token
    token = headers["Authorization"].split(" ", 1)[1]
    claims = decode_tenant_token(token)
    async with tenant_session(claims.tenant_id) as session:
        await tenant_onboarding.seed_tenant_defaults(session)


async def _seed_cash_account(client, headers, initial: int = 0) -> int:
    r = await client.post(
        "/api/v1/cashflow/accounts",
        json={"name": "Касса", "account_type": "cash", "initial_balance": str(initial)},
        headers=headers,
    )
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Manual payments
# ---------------------------------------------------------------------------
async def test_create_payment_marks_order_as_paid(client):
    refs = await _setup_with_order(client, order_amount=5000)
    headers = refs["headers"]

    r = await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"], "amount": "5000", "payment_method": "cash"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "succeeded"

    # Order status стал paid.
    r = await client.get(f"/api/v1/orders/{refs['order_id']}", headers=headers)
    assert r.json()["status"] == "paid"
    assert float(r.json()["paid_amount"]) == 5000.0


async def test_partial_payment_does_not_mark_paid(client):
    refs = await _setup_with_order(client, order_amount=5000)
    headers = refs["headers"]
    r = await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"], "amount": "1000", "payment_method": "cash"},
        headers=headers,
    )
    assert r.status_code == 201
    r = await client.get(f"/api/v1/orders/{refs['order_id']}", headers=headers)
    assert r.json()["status"] != "paid"
    assert float(r.json()["paid_amount"]) == 1000.0


async def test_payment_creates_cashflow_transaction(client):
    refs = await _setup_with_order(client, order_amount=5000)
    headers = refs["headers"]
    await _seed_onboarding(headers)
    aid = await _seed_cash_account(client, headers, initial=0)

    r = await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"], "amount": "5000", "payment_method": "cash"},
        headers=headers,
    )
    assert r.status_code == 201

    # Баланс счёта вырос на 5000.
    r = await client.get(f"/api/v1/cashflow/accounts/{aid}", headers=headers)
    assert float(r.json()["current_balance"]) == 5000.0


async def test_payment_id_mismatch_returns_400(client):
    refs = await _setup_with_order(client)
    headers = refs["headers"]
    r = await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"] + 1000, "amount": "100", "payment_method": "cash"},
        headers=headers,
    )
    assert r.status_code == 400


async def test_list_payments_returns_only_for_this_order(client):
    refs = await _setup_with_order(client, order_amount=1000)
    headers = refs["headers"]
    await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"], "amount": "500", "payment_method": "cash"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/orders/{refs['order_id']}/payments",
        json={"order_id": refs["order_id"], "amount": "500", "payment_method": "card"},
        headers=headers,
    )
    r = await client.get(f"/api/v1/orders/{refs['order_id']}/payments", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# Vehicle history
# ---------------------------------------------------------------------------
async def test_history_returns_orders_for_vehicle(client):
    refs = await _setup_with_order(client, order_amount=5000)
    headers = refs["headers"]

    # Второй заказ для того же ТС.
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": refs["vehicle_id"],
            "order_works": [{"work_name": "Тормоза", "quantity": 1, "price": "3000", "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    assert r.status_code == 201

    r = await client.get(
        f"/api/v1/vehicles/{refs['vehicle_id']}/history", headers=headers
    )
    assert r.status_code == 200
    assert len(r.json()) == 2
    # Новые первые
    assert r.json()[0]["created_at"] >= r.json()[1]["created_at"]


async def test_history_empty_for_unknown_vehicle(client):
    refs = await _setup_with_order(client)
    headers = refs["headers"]
    r = await client.get(
        f"/api/v1/vehicles/{refs['vehicle_id'] + 9999}/history", headers=headers
    )
    assert r.status_code == 404


async def test_history_empty_for_vehicle_without_orders(client):
    refs = await _setup_with_order(client)
    headers = refs["headers"]

    # Создаём второе ТС без заказов.
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Other", "phone": "+7901"}, headers=headers,
    )
    cust = r.json()["id"]
    bid = (await client.get("/api/v1/vehicle-brands/", headers=headers)).json()["brands"][0]["id"]
    mid = (await client.post(
        "/api/v1/vehicle-brands/models", json={"brand_id": bid}, headers=headers
    )).json()["models"][0]["id"]
    r = await client.post(
        "/api/v1/vehicles/",
        json={"customer_id": cust, "brand_id": bid, "model_id": mid, "license_plate": "Б002БВ", "year": 2021},
        headers=headers,
    )
    vid2 = r.json()["id"]

    r = await client.get(f"/api/v1/vehicles/{vid2}/history", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Cross-tenant isolation
# ---------------------------------------------------------------------------
async def test_payment_isolation_between_tenants(client):
    refs_a = await _setup_with_order(client, TENANT_ALPHA, order_amount=1000)
    refs_b = await _setup_with_order(client, TENANT_BETA, order_amount=2000)

    await client.post(
        f"/api/v1/orders/{refs_a['order_id']}/payments",
        json={"order_id": refs_a["order_id"], "amount": "1000", "payment_method": "cash"},
        headers=refs_a["headers"],
    )

    # Beta видит только свои платежи (none).
    r = await client.get(
        f"/api/v1/orders/{refs_b['order_id']}/payments", headers=refs_b["headers"]
    )
    assert r.status_code == 200
    assert len(r.json()) == 0
