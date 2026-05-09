"""End-to-end тесты /api/v1/dashboard/stats."""
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
            "full_name": "Manager", "position": "manager",
            "hire_date": "2026-01-01", "salary_base": "50000",
        },
        headers=bare_h,
    )
    eid = r.json()["id"]
    full = make_token(tenant_id=tenant, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}
    return {"headers": headers, "employee_id": eid}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_stats_without_auth_returns_401(client):
    r = await client.get("/api/v1/dashboard/stats")
    assert r.status_code == 401


async def test_stats_with_invalid_period_returns_422(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/dashboard/stats?period=invalid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_stats_custom_period_requires_dates(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/dashboard/stats?period=custom",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


async def test_stats_custom_period_too_long(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/dashboard/stats?period=custom&date_from=2020-01-01&date_to=2026-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Empty tenant — все метрики на месте, нули.
# ---------------------------------------------------------------------------
async def test_stats_empty_tenant_returns_zeros(client):
    refs = await _setup(client)
    r = await client.get("/api/v1/dashboard/stats", headers=refs["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    # Core fields present.
    assert body["period"] == "month"
    assert body["revenue"]["value"] == 0
    assert body["avg_check"]["value"] == 0
    assert body["orders_count"]["value"] == 0
    assert body["wip_amount"] == 0
    # Pipeline всегда 7 элементов.
    assert len(body["pipeline_7d"]) == 7
    assert body["pipeline_7d"][0]["is_today"] is True
    # Mechanics_stats пуст.
    assert body["mechanics_stats"] == []
    # Alerts на месте.
    assert body["alerts"]["unpaid_orders_count"] == 0
    assert body["alerts"]["no_shows_today"] == 0
    # Revenue chart не пустой (для month — по дням).
    assert isinstance(body["revenue_chart"], list)
    assert len(body["revenue_chart"]) > 0


async def test_stats_period_label_for_month(client):
    refs = await _setup(client)
    r = await client.get(
        "/api/v1/dashboard/stats?period=year", headers=refs["headers"]
    )
    body = r.json()
    # Year-режим: chart по месяцам = 12 точек.
    assert len(body["revenue_chart"]) == 12


async def test_stats_with_completed_order_increases_revenue_and_count(client):
    """Создаём заказ, оплачиваем его, проверяем, что revenue и orders_count выросли."""
    refs = await _setup(client)
    headers = refs["headers"]

    # Customer + brand/model + vehicle + order.
    r = await client.post(
        "/api/v1/customers/", json={"full_name": "X", "phone": "+79001234567"},
        headers=headers,
    )
    cust = r.json()["id"]
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Toyota", "models": ["Camry"]}]},
        headers=headers,
    )
    brands = (await client.get("/api/v1/vehicle-brands/", headers=headers)).json()["brands"]
    bid = brands[0]["id"]
    mid = (await client.post(
        "/api/v1/vehicle-brands/models", json={"brand_id": bid}, headers=headers
    )).json()["models"][0]["id"]
    r = await client.post(
        "/api/v1/vehicles/",
        json={"customer_id": cust, "brand_id": bid, "model_id": mid, "license_plate": "А", "year": 2020},
        headers=headers,
    )
    vid = r.json()["id"]
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": vid,
            "order_works": [{"work_name": "test", "quantity": 1, "price": "1000", "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    oid = r.json()["id"]

    # Оплачиваем.
    await client.post(
        f"/api/v1/orders/{oid}/payments",
        json={"order_id": oid, "amount": "1000", "payment_method": "cash"},
        headers=headers,
    )

    r = await client.get("/api/v1/dashboard/stats", headers=headers)
    body = r.json()
    assert body["revenue"]["value"] == 1000
    assert body["orders_count"]["value"] == 1
    assert body["avg_check"]["value"] == 1000


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
async def test_isolation_between_tenants(client):
    refs_a = await _setup(client, TENANT_ALPHA)
    refs_b = await _setup(client, TENANT_BETA)

    # Beta создаёт заказ.
    headers_b = refs_b["headers"]
    r = await client.post(
        "/api/v1/customers/", json={"full_name": "Beta", "phone": "+79001234567"},
        headers=headers_b,
    )
    cust = r.json()["id"]
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "B", "models": ["M"]}]},
        headers=headers_b,
    )
    bid = (await client.get("/api/v1/vehicle-brands/", headers=headers_b)).json()["brands"][0]["id"]
    mid = (await client.post(
        "/api/v1/vehicle-brands/models", json={"brand_id": bid}, headers=headers_b
    )).json()["models"][0]["id"]
    r = await client.post(
        "/api/v1/vehicles/",
        json={"customer_id": cust, "brand_id": bid, "model_id": mid, "license_plate": "Б", "year": 2020},
        headers=headers_b,
    )
    vid = r.json()["id"]
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": vid,
            "order_works": [{"work_name": "test", "quantity": 1, "price": "5000", "discount": 0}],
            "order_parts": [],
        },
        headers=headers_b,
    )
    oid = r.json()["id"]
    await client.post(
        f"/api/v1/orders/{oid}/payments",
        json={"order_id": oid, "amount": "5000", "payment_method": "cash"},
        headers=headers_b,
    )

    # Alpha-дашборд не должен видеть Beta-данные.
    r = await client.get("/api/v1/dashboard/stats", headers=refs_a["headers"])
    body = r.json()
    assert body["revenue"]["value"] == 0
    assert body["orders_count"]["value"] == 0
