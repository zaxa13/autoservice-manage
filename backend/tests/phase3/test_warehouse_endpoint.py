"""End-to-end тесты /api/v1/warehouse."""
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


async def _seed_part(client, headers, name="Фильтр", part_number="FIL-001", price="500") -> int:
    r = await client.post(
        "/api/v1/parts/",
        json={"name": name, "part_number": part_number, "price": price, "category": "consumables"},
        headers=headers,
    )
    return r.json()["id"]


async def _seed_supplier(client, headers, name="Поставщик 1") -> int:
    r = await client.post(
        "/api/v1/suppliers/", json={"name": name}, headers=headers
    )
    return r.json()["id"]


async def _seed_employee(client, admin_headers) -> int:
    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "Кладовщик",
            "position": "manager",
            "hire_date": "2026-01-01",
            "salary_base": "50000",
        },
        headers=admin_headers,
    )
    return r.json()["id"]


async def _setup_tenant(client, tenant=TENANT_ALPHA) -> tuple[dict, dict]:
    """Возвращает (admin_headers, refs)."""
    bare = make_token(tenant_id=tenant, roles=["admin"])
    bare_headers = {"Authorization": f"Bearer {bare}"}
    eid = await _seed_employee(client, bare_headers)
    full = make_token(tenant_id=tenant, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full}"}
    refs = {
        "employee_id": eid,
        "part_id": await _seed_part(client, headers),
        "supplier_id": await _seed_supplier(client, headers),
    }
    return headers, refs


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_list_items_requires_auth(client):
    r = await client.get("/api/v1/warehouse/items")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Items + transactions
# ---------------------------------------------------------------------------
async def test_create_item_and_increment_via_incoming(client):
    headers, refs = await _setup_tenant(client)

    r = await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": refs["part_id"], "quantity": "0", "min_quantity": "5"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    item_id = r.json()["id"]

    r = await client.post(
        "/api/v1/warehouse/transactions/incoming",
        json={
            "warehouse_item_id": item_id,
            "transaction_type": "incoming",
            "quantity": "10",
            "price": "100",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = await client.get(f"/api/v1/warehouse/items/{item_id}", headers=headers)
    assert float(r.json()["quantity"]) == 10.0


async def test_adjustment_can_decrement(client):
    headers, refs = await _setup_tenant(client)
    r = await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": refs["part_id"], "quantity": "10", "min_quantity": "0"},
        headers=headers,
    )
    item_id = r.json()["id"]

    r = await client.post(
        "/api/v1/warehouse/transactions/adjustment",
        json={"warehouse_item_id": item_id, "quantity_delta": "-3", "reason": "списание"},
        headers=headers,
    )
    assert r.status_code == 201

    r = await client.get(f"/api/v1/warehouse/items/{item_id}", headers=headers)
    assert float(r.json()["quantity"]) == 7.0


async def test_adjustment_below_zero_returns_400(client):
    headers, refs = await _setup_tenant(client)
    r = await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": refs["part_id"], "quantity": "5", "min_quantity": "0"},
        headers=headers,
    )
    item_id = r.json()["id"]
    r = await client.post(
        "/api/v1/warehouse/transactions/adjustment",
        json={"warehouse_item_id": item_id, "quantity_delta": "-10"},
        headers=headers,
    )
    assert r.status_code == 400


async def test_low_stock_returns_only_below_min(client):
    headers, refs = await _setup_tenant(client)
    p2 = await _seed_part(client, headers, "Фильтр 2", "FIL-002")
    # item1 — ниже минимума, item2 — ОК
    await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": refs["part_id"], "quantity": "1", "min_quantity": "5"},
        headers=headers,
    )
    await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": p2, "quantity": "10", "min_quantity": "5"},
        headers=headers,
    )
    r = await client.get("/api/v1/warehouse/low-stock", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["part_id"] == refs["part_id"]


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
async def test_create_receipt_and_post_increases_stock(client):
    headers, refs = await _setup_tenant(client)

    body = {
        "document_date": "2026-05-09",
        "supplier_id": refs["supplier_id"],
        "supplier_document_number": "SUP-1",
        "lines": [
            {
                "part_id": refs["part_id"],
                "quantity": "20",
                "purchase_price": "80",
                "sale_price": "150",
            }
        ],
    }
    r = await client.post("/api/v1/warehouse/receipts", json=body, headers=headers)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["number"] == "НП-001"
    assert r.json()["status"] == "draft"
    assert float(r.json()["total_amount"]) == 1600.0  # 20 * 80

    r = await client.post(
        f"/api/v1/warehouse/receipts/{rid}/post", headers=headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "posted"

    # Создаётся WarehouseItem для part_id (если не было) с quantity=20.
    r = await client.get(
        f"/api/v1/warehouse/items?part_number=FIL-001", headers=headers
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert float(r.json()[0]["quantity"]) == 20.0


async def test_post_already_posted_receipt_returns_400(client):
    headers, refs = await _setup_tenant(client)
    body = {
        "document_date": "2026-05-09",
        "supplier_id": refs["supplier_id"],
        "lines": [{"part_id": refs["part_id"], "quantity": "5", "purchase_price": "80", "sale_price": "150"}],
    }
    r = await client.post("/api/v1/warehouse/receipts", json=body, headers=headers)
    rid = r.json()["id"]
    await client.post(f"/api/v1/warehouse/receipts/{rid}/post", headers=headers)
    r = await client.post(f"/api/v1/warehouse/receipts/{rid}/post", headers=headers)
    assert r.status_code == 400


async def test_update_posted_receipt_returns_400(client):
    headers, refs = await _setup_tenant(client)
    body = {
        "document_date": "2026-05-09",
        "supplier_id": refs["supplier_id"],
        "lines": [{"part_id": refs["part_id"], "quantity": "5", "purchase_price": "80", "sale_price": "150"}],
    }
    r = await client.post("/api/v1/warehouse/receipts", json=body, headers=headers)
    rid = r.json()["id"]
    await client.post(f"/api/v1/warehouse/receipts/{rid}/post", headers=headers)

    r = await client.put(
        f"/api/v1/warehouse/receipts/{rid}",
        json={"supplier_document_number": "X"},
        headers=headers,
    )
    assert r.status_code == 400


async def test_receipt_number_is_per_tenant(client):
    h_a, refs_a = await _setup_tenant(client, TENANT_ALPHA)
    h_b, refs_b = await _setup_tenant(client, TENANT_BETA)
    body_a = {
        "document_date": "2026-05-09",
        "supplier_id": refs_a["supplier_id"],
        "lines": [{"part_id": refs_a["part_id"], "quantity": "1", "purchase_price": "1", "sale_price": "2"}],
    }
    body_b = {
        "document_date": "2026-05-09",
        "supplier_id": refs_b["supplier_id"],
        "lines": [{"part_id": refs_b["part_id"], "quantity": "1", "purchase_price": "1", "sale_price": "2"}],
    }
    r_a = await client.post("/api/v1/warehouse/receipts", json=body_a, headers=h_a)
    r_b = await client.post("/api/v1/warehouse/receipts", json=body_b, headers=h_b)
    assert r_a.json()["number"] == "НП-001"
    assert r_b.json()["number"] == "НП-001"  # Beta стартует свой счётчик


async def test_supplier_receipts_report(client):
    headers, refs = await _setup_tenant(client)
    body = {
        "document_date": "2026-05-09",
        "supplier_id": refs["supplier_id"],
        "lines": [{"part_id": refs["part_id"], "quantity": "10", "purchase_price": "50", "sale_price": "100"}],
    }
    await client.post("/api/v1/warehouse/receipts", json=body, headers=headers)

    r = await client.get(
        f"/api/v1/warehouse/reports/supplier-receipts?supplier_id={refs['supplier_id']}",
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_count"] == 1
    assert float(body["total_amount"]) == 500.0


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
async def test_isolation_between_tenants(client):
    h_a, refs_a = await _setup_tenant(client, TENANT_ALPHA)
    h_b, _refs_b = await _setup_tenant(client, TENANT_BETA)

    await client.post(
        "/api/v1/warehouse/items",
        json={"part_id": refs_a["part_id"], "quantity": "10", "min_quantity": "0"},
        headers=h_a,
    )

    r = await client.get("/api/v1/warehouse/items", headers=h_b)
    assert r.status_code == 200
    assert len(r.json()) == 0
