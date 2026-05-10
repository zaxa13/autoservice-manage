"""End-to-end тесты /api/v1/integrations и /api/v1/payments/yookassa.

Внешний HTTP подменяется через httpx.MockTransport. Никаких реальных
сетевых запросов наружу из тестов.
"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
import pytest_asyncio

from .conftest import TENANT_ALPHA, TENANT_BETA, make_token

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Mock transport setup
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_external_http(monkeypatch):
    """Подменяет httpx.AsyncClient transport во всех интеграциях.

    Маршрутизирует по pathname: /vehicle/check (gibdd), /search,
    /orders (parts_suppliers), /v3/payments (yookassa).
    """
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/vehicle/check"):
            body = json.loads(request.content.decode())
            return httpx.Response(200, json={
                "vin": body.get("vin"), "registered": True, "stolen": False,
            })
        if path.endswith("/search"):
            return httpx.Response(200, json={
                "results": [{"name": "Test", "price": "100"}],
            })
        if path.endswith("/orders"):
            return httpx.Response(200, json={"order_id": "EXT-123"})
        if path.endswith("/v3/payments"):
            return httpx.Response(200, json={
                "id": "yk_pay_123",
                "status": "pending",
                "confirmation": {"confirmation_url": "https://yk.ru/confirm/123"},
            })
        return httpx.Response(404, json={"error": "unknown endpoint"})

    from app.integrations import _helpers
    monkeypatch.setattr(_helpers, "_TRANSPORT", httpx.MockTransport(handler))
    yield


@pytest.fixture
def app():
    from app.main import app as main_app
    return main_app


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# GIBDD
# ---------------------------------------------------------------------------
async def test_gibdd_check_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.get(
        "/api/v1/integrations/gibdd/vehicle/JT12345678",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_gibdd_check_success(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/integrations/gibdd/vehicle/JT12345678",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["error"] is None
    assert body["data"]["vin"] == "JT12345678"
    assert body["data"]["registered"] is True


# ---------------------------------------------------------------------------
# Parts suppliers
# ---------------------------------------------------------------------------
async def test_parts_search_success(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/integrations/suppliers/search?query=oil-filter",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "Test"


async def test_parts_search_query_min_length(client):
    """min_length=2 → query='a' даст 422."""
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.get(
        "/api/v1/integrations/suppliers/search?query=a",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_supplier_order_success(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/integrations/suppliers/order",
        json={
            "supplier_id": "ext-supplier-1",
            "items": [{"part_number": "FIL-001", "quantity": 5}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["order_id"] == "EXT-123"


# ---------------------------------------------------------------------------
# Integration logs создаются
# ---------------------------------------------------------------------------
async def test_gibdd_call_creates_integration_log(client, migrator_conn):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    await client.get(
        "/api/v1/integrations/gibdd/vehicle/JT99",
        headers={"Authorization": f"Bearer {token}"},
    )
    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT integration_type, status FROM app.integration_logs "
            "WHERE tenant_id = %s",
            (str(TENANT_ALPHA),),
        )
        rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0] == ("gibdd", "success")


# ---------------------------------------------------------------------------
# YooKassa create + webhook
# ---------------------------------------------------------------------------
async def _setup_order(client, headers) -> int:
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "X", "phone": "+79001234567"}, headers=headers,
    )
    cust = r.json()["id"]
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "T", "models": ["M"]}]},
        headers=headers,
    )
    bid = (await client.get("/api/v1/vehicle-brands/", headers=headers)).json()["brands"][0]["id"]
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
            "order_works": [{"work_name": "X", "quantity": 1, "price": "1000", "discount": 0}],
            "order_parts": [],
        },
        headers=headers,
    )
    return r.json()["id"]


async def test_yookassa_create_payment(client):
    bare = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    bare_h = {"Authorization": f"Bearer {bare}"}
    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "M", "position": "manager",
            "hire_date": "2026-01-01", "salary_base": "50000",
        },
        headers=bare_h,
    )
    eid = r.json()["id"]
    full = make_token(tenant_id=TENANT_ALPHA, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}

    oid = await _setup_order(client, headers)

    r = await client.post(
        "/api/v1/payments/yookassa/create",
        json={"order_id": oid, "amount": "1000"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["yookassa_payment_id"] == "yk_pay_123"
    assert body["confirmation_url"] == "https://yk.ru/confirm/123"


async def test_yookassa_webhook_succeeded_marks_payment_and_updates_order(client, migrator_conn):
    bare = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    bare_h = {"Authorization": f"Bearer {bare}"}
    r = await client.post(
        "/api/v1/employees/",
        json={"full_name": "M", "position": "manager", "hire_date": "2026-01-01", "salary_base": "50000"},
        headers=bare_h,
    )
    eid = r.json()["id"]
    full = make_token(tenant_id=TENANT_ALPHA, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}
    oid = await _setup_order(client, headers)

    # Создаём ЮКасса-платёж (pending).
    r = await client.post(
        "/api/v1/payments/yookassa/create",
        json={"order_id": oid, "amount": "1000"},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    # Шлём webhook (без auth) с metadata={tenant_id, order_id}.
    webhook_body = {
        "event": "payment.succeeded",
        "object": {
            "id": "yk_pay_123",
            "status": "succeeded",
            "metadata": {"tenant_id": str(TENANT_ALPHA), "order_id": str(oid)},
        },
    }
    r = await client.post("/api/v1/payments/yookassa/webhook", json=webhook_body)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # Проверяем через migrator (BYPASSRLS): payment.status=succeeded,
    # order.paid_amount=1000.
    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT status, amount FROM app.payments WHERE yookassa_payment_id='yk_pay_123'"
        )
        st, amt = cur.fetchone()
        assert st == "succeeded"
        assert float(amt) == 1000.0
        cur.execute("SELECT paid_amount FROM app.orders WHERE id = %s", (oid,))
        assert float(cur.fetchone()[0]) == 1000.0


async def test_yookassa_webhook_without_metadata_returns_error(client):
    r = await client.post(
        "/api/v1/payments/yookassa/webhook",
        json={"object": {"id": "x"}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "error"


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
async def test_integration_logs_isolated_per_tenant(client, migrator_conn):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    await client.get(
        "/api/v1/integrations/gibdd/vehicle/JT99",
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.get(
        "/api/v1/integrations/gibdd/vehicle/JT99",
        headers={"Authorization": f"Bearer {t_b}"},
    )
    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT tenant_id::text, count(*) FROM app.integration_logs "
            "GROUP BY tenant_id ORDER BY tenant_id"
        )
        rows = cur.fetchall()
    counts = {r[0]: r[1] for r in rows}
    assert counts[str(TENANT_ALPHA)] == 1
    assert counts[str(TENANT_BETA)] == 1
