"""End-to-end тесты /api/v1/orders."""
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


async def _bootstrap_refs(client, headers) -> dict:
    """Создаёт customer/brand/model/vehicle/employee и возвращает их id."""
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Owner", "phone": "+7900"},
        headers=headers,
    )
    customer_id = r.json()["id"]
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Toyota", "models": ["Camry"]}]},
        headers=headers,
    )
    r = await client.get("/api/v1/vehicle-brands/", headers=headers)
    brand_id = r.json()["brands"][0]["id"]
    r = await client.post(
        "/api/v1/vehicle-brands/models",
        json={"brand_id": brand_id},
        headers=headers,
    )
    model_id = r.json()["models"][0]["id"]
    r = await client.post(
        "/api/v1/vehicles/",
        json={
            "customer_id": customer_id,
            "brand_id": brand_id,
            "model_id": model_id,
            "license_plate": "А001АА",
            "year": 2020,
        },
        headers=headers,
    )
    vehicle_id = r.json()["id"]
    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "Manager",
            "position": "manager",
            "hire_date": "2026-01-01",
            "salary_base": "50000",
        },
        headers=headers,
    )
    employee_id = r.json()["id"]
    return {"vehicle_id": vehicle_id, "employee_id": employee_id, "customer_id": customer_id}


async def _token_with_employee(client, tenant=TENANT_ALPHA):
    """Создаёт employee и возвращает (admin_headers, refs, employee_id)."""
    admin_token = make_token(tenant_id=tenant, roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    refs = await _bootstrap_refs(client, headers)
    # Токен от имени конкретного сотрудника
    full_token = make_token(tenant_id=tenant, roles=["admin"], employee_id=refs["employee_id"])
    return {"Authorization": f"Bearer {full_token}"}, refs


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/orders/")
    assert r.status_code == 401


async def test_create_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"], employee_id=1)
    r = await client.post(
        "/api/v1/orders/",
        json={"vehicle_id": 1, "order_works": [], "order_parts": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_create_without_employee_id_returns_400(client):
    """Токен admin без employee_id → 400 на /orders POST."""
    headers, refs = await _token_with_employee(client)
    bad_token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])  # no employee_id
    r = await client.post(
        "/api/v1/orders/",
        json={"vehicle_id": refs["vehicle_id"], "order_works": [], "order_parts": []},
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
async def test_create_order_with_works_and_parts(client):
    headers, refs = await _token_with_employee(client)
    body = {
        "vehicle_id": refs["vehicle_id"],
        "order_works": [
            {"work_name": "Замена масла", "quantity": 1, "price": "1500", "discount": 0}
        ],
        "order_parts": [
            {"part_name": "Масло 5W30", "quantity": 4, "price": "500", "discount": 10}
        ],
    }
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["number"] == "ЗН-001"
    assert order["status"] == "new"
    # works total = 1500, parts total = 4*500*0.9 = 1800, итого 3300
    assert float(order["total_amount"]) == 3300.0


async def test_order_number_increments_per_tenant(client):
    headers_a, refs_a = await _token_with_employee(client, TENANT_ALPHA)
    headers_b, refs_b = await _token_with_employee(client, TENANT_BETA)

    body_a = {"vehicle_id": refs_a["vehicle_id"], "order_works": [], "order_parts": []}
    body_b = {"vehicle_id": refs_b["vehicle_id"], "order_works": [], "order_parts": []}

    r1 = await client.post("/api/v1/orders/", json=body_a, headers=headers_a)
    r2 = await client.post("/api/v1/orders/", json=body_a, headers=headers_a)
    r3 = await client.post("/api/v1/orders/", json=body_b, headers=headers_b)

    assert r1.json()["number"] == "ЗН-001"
    assert r2.json()["number"] == "ЗН-002"
    # Beta стартует свой счётчик с нуля
    assert r3.json()["number"] == "ЗН-001"


async def test_get_order_detail_includes_works_and_parts(client):
    headers, refs = await _token_with_employee(client)
    body = {
        "vehicle_id": refs["vehicle_id"],
        "order_works": [{"work_name": "Тест", "quantity": 1, "price": "100", "discount": 0}],
        "order_parts": [{"part_name": "Деталь", "quantity": 2, "price": "50", "discount": 0}],
    }
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    order_id = r.json()["id"]
    r = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["order_works"]) == 1
    assert len(detail["order_parts"]) == 1
    assert detail["vehicle"]["license_plate"] == "А001АА"


async def test_update_replaces_works(client):
    headers, refs = await _token_with_employee(client)
    body = {
        "vehicle_id": refs["vehicle_id"],
        "order_works": [{"work_name": "Старая", "quantity": 1, "price": "100", "discount": 0}],
        "order_parts": [],
    }
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    order_id = r.json()["id"]

    # Update — заменить works на новые
    update_body = {
        "order_works": [
            {"work_name": "Новая 1", "quantity": 2, "price": "200", "discount": 0},
            {"work_name": "Новая 2", "quantity": 1, "price": "300", "discount": 0},
        ]
    }
    r = await client.put(f"/api/v1/orders/{order_id}", json=update_body, headers=headers)
    assert r.status_code == 200
    # 2*200 + 300 = 700
    assert float(r.json()["total_amount"]) == 700.0


async def test_cancel_order(client):
    headers, refs = await _token_with_employee(client)
    body = {"vehicle_id": refs["vehicle_id"], "order_works": [], "order_parts": []}
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    order_id = r.json()["id"]
    r = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_complete_order(client):
    headers, refs = await _token_with_employee(client)
    body = {"vehicle_id": refs["vehicle_id"], "order_works": [], "order_parts": []}
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    order_id = r.json()["id"]
    r = await client.post(f"/api/v1/orders/{order_id}/complete", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["completed_at"] is not None


async def test_delete_requires_admin(client):
    headers, refs = await _token_with_employee(client)
    body = {"vehicle_id": refs["vehicle_id"], "order_works": [], "order_parts": []}
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    order_id = r.json()["id"]

    manager_token = make_token(
        tenant_id=TENANT_ALPHA, roles=["manager"], employee_id=refs["employee_id"]
    )
    r = await client.delete(
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r.status_code == 403

    r = await client.delete(f"/api/v1/orders/{order_id}", headers=headers)
    assert r.status_code == 204


async def test_filter_by_status(client):
    headers, refs = await _token_with_employee(client)
    body = {"vehicle_id": refs["vehicle_id"], "order_works": [], "order_parts": []}
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    o1 = r.json()["id"]
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    r = await client.post(f"/api/v1/orders/{o1}/cancel", headers=headers)

    r = await client.get("/api/v1/orders/?status=cancelled", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == o1


async def test_isolation_between_tenants(client):
    headers_a, refs_a = await _token_with_employee(client, TENANT_ALPHA)
    headers_b, refs_b = await _token_with_employee(client, TENANT_BETA)

    body_a = {"vehicle_id": refs_a["vehicle_id"], "order_works": [], "order_parts": []}
    body_b = {"vehicle_id": refs_b["vehicle_id"], "order_works": [], "order_parts": []}

    await client.post("/api/v1/orders/", json=body_a, headers=headers_a)
    await client.post("/api/v1/orders/", json=body_b, headers=headers_b)

    r_a = await client.get("/api/v1/orders/", headers=headers_a)
    r_b = await client.get("/api/v1/orders/", headers=headers_b)
    assert len(r_a.json()) == 1
    assert len(r_b.json()) == 1


async def test_create_with_unknown_vehicle_returns_404(client):
    headers, _refs = await _token_with_employee(client)
    body = {"vehicle_id": 99999, "order_works": [], "order_parts": []}
    r = await client.post("/api/v1/orders/", json=body, headers=headers)
    assert r.status_code == 404


async def test_statuses_lookup_no_auth(client):
    r = await client.get("/api/v1/orders/statuses")
    assert r.status_code == 200
    values = {s["value"] for s in r.json()}
    # COMPLETED исключён из списка (ставится через /complete)
    assert "completed" not in values
    assert "new" in values
    assert "cancelled" in values
