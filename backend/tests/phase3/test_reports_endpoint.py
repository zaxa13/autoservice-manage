"""End-to-end тесты /api/v1/reports."""
from __future__ import annotations

from datetime import date

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


async def _setup(client, tenant=TENANT_ALPHA) -> dict:
    bare = make_token(tenant_id=tenant, roles=["admin"])
    bare_h = {"Authorization": f"Bearer {bare}"}
    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "Манагер", "position": "manager",
            "hire_date": "2026-01-01", "salary_base": "50000",
        },
        headers=bare_h,
    )
    eid = r.json()["id"]
    full = make_token(tenant_id=tenant, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}
    return {"headers": headers, "employee_id": eid}


async def _setup_full(client, tenant=TENANT_ALPHA) -> dict:
    """Полная заготовка: customer + brand/model + vehicle + part."""
    refs = await _setup(client, tenant)
    headers = refs["headers"]
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Клиент", "phone": "+79001234567"},
        headers=headers,
    )
    refs["customer_id"] = r.json()["id"]

    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Toyota", "models": ["Camry"]}]},
        headers=headers,
    )
    bid = (await client.get("/api/v1/vehicle-brands/", headers=headers)).json()["brands"][0]["id"]
    mid = (await client.post(
        "/api/v1/vehicle-brands/models", json={"brand_id": bid}, headers=headers
    )).json()["models"][0]["id"]
    refs["brand_id"] = bid
    refs["model_id"] = mid

    r = await client.post(
        "/api/v1/vehicles/",
        json={
            "customer_id": refs["customer_id"], "brand_id": bid, "model_id": mid,
            "license_plate": "А001АА", "year": 2020,
        },
        headers=headers,
    )
    refs["vehicle_id"] = r.json()["id"]

    r = await client.post(
        "/api/v1/parts/",
        json={
            "name": "Фильтр", "part_number": "FIL-001",
            "price": "500", "category": "consumables"
        },
        headers=headers,
    )
    refs["part_id"] = r.json()["id"]
    return refs


async def _create_paid_order(
    client, headers, vehicle_id, *, work_price="1000", part_price=None, part_id=None
):
    """Создаёт заказ с одной работой (+опционально запчастью), сразу оплачивает целиком."""
    parts = []
    if part_price and part_id:
        parts = [{"part_id": part_id, "quantity": 1, "price": str(part_price), "discount": 0}]
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": vehicle_id,
            "order_works": [{"work_name": "Замена масла", "quantity": 1, "price": str(work_price), "discount": 0}],
            "order_parts": parts,
        },
        headers=headers,
    )
    oid = r.json()["id"]
    total = float(r.json()["total_amount"])
    await client.post(
        f"/api/v1/orders/{oid}/payments",
        json={"order_id": oid, "amount": str(total), "payment_method": "cash"},
        headers=headers,
    )
    return oid


# ---------------------------------------------------------------------------
# Auth + validation
# ---------------------------------------------------------------------------
async def test_revenue_without_auth_returns_401(client):
    r = await client.get("/api/v1/reports/revenue?date_from=2026-05-01&date_to=2026-05-31")
    assert r.status_code == 401


async def test_revenue_invalid_range(client):
    refs = await _setup(client)
    r = await client.get(
        "/api/v1/reports/revenue?date_from=2026-05-31&date_to=2026-05-01",
        headers=refs["headers"],
    )
    assert r.status_code == 400


async def test_revenue_period_too_long(client):
    refs = await _setup(client)
    r = await client.get(
        "/api/v1/reports/revenue?date_from=2020-01-01&date_to=2026-01-01",
        headers=refs["headers"],
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------
async def test_revenue_empty_returns_zeros(client):
    refs = await _setup(client)
    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/revenue?date_from={today}&date_to={today}",
        headers=refs["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_revenue"] == 0
    assert body["total_orders"] == 0
    assert body["avg_check"] == 0


async def test_revenue_with_paid_orders(client):
    refs = await _setup_full(client)
    today = date.today().isoformat()
    await _create_paid_order(client, refs["headers"], refs["vehicle_id"], work_price="3000")
    await _create_paid_order(client, refs["headers"], refs["vehicle_id"], work_price="2000")

    r = await client.get(
        f"/api/v1/reports/revenue?date_from={today}&date_to={today}",
        headers=refs["headers"],
    )
    body = r.json()
    assert body["total_revenue"] == 5000
    assert body["total_orders"] == 2
    assert body["avg_check"] == 2500
    assert len(body["by_day"]) == 1
    assert body["by_day"][0]["revenue"] == 5000
    # Платежи cash
    assert any(m["method"] == "cash" and m["amount"] == 5000 for m in body["by_payment_method"])


# ---------------------------------------------------------------------------
# Mechanics
# ---------------------------------------------------------------------------
async def test_mechanics_empty(client):
    refs = await _setup(client)
    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/mechanics?date_from={today}&date_to={today}",
        headers=refs["headers"],
    )
    assert r.status_code == 200
    assert r.json()["mechanics"] == []
    assert r.json()["team_total_revenue"] == 0


async def test_mechanics_with_completed_orders(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    today = date.today().isoformat()

    # Создаём заказ с работой, выполненной механиком (=employee_id из claims).
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": refs["vehicle_id"],
            "mechanic_id": refs["employee_id"],
            "order_works": [{"work_name": "Тест", "mechanic_id": refs["employee_id"],
                             "quantity": 1, "price": "4000", "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    oid = r.json()["id"]
    await client.post(
        f"/api/v1/orders/{oid}/payments",
        json={"order_id": oid, "amount": "4000", "payment_method": "cash"},
        headers=headers,
    )

    r = await client.get(
        f"/api/v1/reports/mechanics?date_from={today}&date_to={today}",
        headers=headers,
    )
    body = r.json()
    assert body["team_total_orders"] == 1
    assert body["team_total_revenue"] == 4000
    assert len(body["mechanics"]) == 1
    assert body["mechanics"][0]["full_name"] == "Манагер"
    assert body["mechanics"][0]["orders_completed"] == 1
    assert body["mechanics"][0]["revenue"] == 4000
    assert body["mechanics"][0]["works_count"] == 1


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
async def test_orders_report_empty(client):
    refs = await _setup(client)
    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/orders?date_from={today}&date_to={today}",
        headers=refs["headers"],
    )
    assert r.status_code == 200
    assert r.json()["total_count"] == 0


async def test_orders_report_by_status(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    today = date.today().isoformat()
    o1 = await _create_paid_order(client, headers, refs["vehicle_id"], work_price="100")
    # Cancelled order.
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": refs["vehicle_id"],
            "order_works": [{"work_name": "X", "quantity": 1, "price": "200", "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    o2 = r.json()["id"]
    await client.post(f"/api/v1/orders/{o2}/cancel", headers=headers)

    r = await client.get(
        f"/api/v1/reports/orders?date_from={today}&date_to={today}",
        headers=headers,
    )
    body = r.json()
    assert body["total_count"] == 2
    statuses = {item["status"]: item["count"] for item in body["by_status"]}
    assert statuses.get("paid") == 1
    assert statuses.get("cancelled") == 1


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
async def test_parts_report_with_used_part(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    today = date.today().isoformat()

    await _create_paid_order(
        client, headers, refs["vehicle_id"],
        work_price="500", part_price="500", part_id=refs["part_id"]
    )

    r = await client.get(
        f"/api/v1/reports/parts?date_from={today}&date_to={today}",
        headers=headers,
    )
    body = r.json()
    assert body["total_parts_revenue"] == 500
    assert body["total_quantity_sold"] == 1
    assert len(body["top_parts"]) == 1
    assert body["top_parts"][0]["part_number"] == "FIL-001"


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
async def test_isolation_between_tenants(client):
    refs_a = await _setup_full(client, TENANT_ALPHA)
    refs_b = await _setup_full(client, TENANT_BETA)
    today = date.today().isoformat()

    await _create_paid_order(client, refs_b["headers"], refs_b["vehicle_id"], work_price="9999")
    r = await client.get(
        f"/api/v1/reports/revenue?date_from={today}&date_to={today}",
        headers=refs_a["headers"],
    )
    assert r.json()["total_revenue"] == 0
