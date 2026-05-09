"""End-to-end тесты /api/v1/salary."""
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


async def _setup_full(client, tenant=TENANT_ALPHA) -> dict:
    """Создаёт тенант со всем нужным для расчёта зарплаты:
    employee, vehicle, brand, model, customer, account, category «Зарплата».
    Возвращает headers (с employee_id) и refs.
    """
    bare_token = make_token(tenant_id=tenant, roles=["admin"])
    bare_headers = {"Authorization": f"Bearer {bare_token}"}

    r = await client.post(
        "/api/v1/employees/",
        json={
            "full_name": "Иванов И.",
            "position": "mechanic",
            "hire_date": "2026-01-01",
            "salary_base": "30000",
        },
        headers=bare_headers,
    )
    eid = r.json()["id"]

    full_token = make_token(tenant_id=tenant, roles=["admin"], employee_id=eid)
    headers = {"Authorization": f"Bearer {full_token}"}

    # Customer / brand / model / vehicle.
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Owner", "phone": "+7900"}, headers=headers,
    )
    cust_id = r.json()["id"]
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
            "customer_id": cust_id, "brand_id": bid, "model_id": mid,
            "license_plate": "А001АА", "year": 2020,
        },
        headers=headers,
    )
    vid = r.json()["id"]

    # Cashflow account + system salary category.
    r = await client.post(
        "/api/v1/cashflow/accounts",
        json={"name": "Касса", "account_type": "cash", "initial_balance": "100000"},
        headers=headers,
    )
    acc_id = r.json()["id"]

    return {
        "headers": headers,
        "bare_headers": bare_headers,
        "employee_id": eid,
        "vehicle_id": vid,
        "account_id": acc_id,
    }


async def _seed_system_salary_category(client, headers):
    """Создаём системную категорию «Зарплата» (онбординг ещё не запущен)."""
    # Через прямую регистрацию категории + флаг is_system нельзя — POST создаёт только пользовательские.
    # Поэтому вызовем onboarding-сервис напрямую через миграторскую сессию:
    # для тестов проще создать обычную (non-system) категорию с тем же name
    # и обновить флаг через миграторский INSERT.
    # Альтернатива — фактически вызвать seed_tenant_defaults. Сделаем это:
    from app.database import tenant_session
    from app.services import tenant_onboarding
    import uuid as _uuid
    # Из заголовка Authorization извлекаем JWT и из него tenant_id.
    from app.core.security import decode_tenant_token
    token = headers["Authorization"].split(" ", 1)[1]
    claims = decode_tenant_token(token)
    async with tenant_session(claims.tenant_id) as session:
        await tenant_onboarding.seed_tenant_defaults(session)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_list_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.get(
        "/api/v1/salary/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_accountant_can_list(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["accountant"])
    r = await client.get(
        "/api/v1/salary/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Scheme
# ---------------------------------------------------------------------------
async def test_get_scheme_returns_empty_for_employee_without_scheme(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    r = await client.get(
        f"/api/v1/salary/scheme/{refs['employee_id']}", headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] is None
    assert float(body["works_percentage"]) == 0.0


async def test_set_and_get_scheme(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    r = await client.put(
        f"/api/v1/salary/scheme/{refs['employee_id']}",
        json={"works_percentage": "30", "revenue_percentage": "5"},
        headers=headers,
    )
    assert r.status_code == 200
    assert float(r.json()["works_percentage"]) == 30.0

    r = await client.get(
        f"/api/v1/salary/scheme/{refs['employee_id']}", headers=headers
    )
    assert float(r.json()["works_percentage"]) == 30.0
    assert float(r.json()["revenue_percentage"]) == 5.0


# ---------------------------------------------------------------------------
# Calculate
# ---------------------------------------------------------------------------
async def test_calculate_with_no_scheme_uses_only_base(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": refs["employee_id"],
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    s = r.json()
    assert float(s["base_salary"]) == 30000.0
    assert float(s["bonus"]) == 0.0
    assert float(s["total"]) == 30000.0
    assert s["status"] == "calculated"


async def test_calculate_with_works_bonus(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    eid = refs["employee_id"]

    # Set scheme: 20% от работ.
    await client.put(
        f"/api/v1/salary/scheme/{eid}",
        json={"works_percentage": "20", "revenue_percentage": "0"},
        headers=headers,
    )

    # Создаём заказ с работой механика и закрываем его.
    r = await client.post(
        "/api/v1/orders/",
        json={
            "vehicle_id": refs["vehicle_id"],
            "mechanic_id": eid,
            "order_works": [
                {"work_name": "Замена масла", "mechanic_id": eid,
                 "quantity": 1, "price": "5000", "discount": 0}
            ],
            "order_parts": [],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    oid = r.json()["id"]
    r = await client.post(f"/api/v1/orders/{oid}/complete", headers=headers)
    assert r.status_code == 200

    # Расчёт за май.
    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": eid,
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers=headers,
    )
    assert r.status_code == 201
    s = r.json()
    # works_bonus = 5000 * 20% = 1000
    assert float(s["bonus"]) == 1000.0
    assert float(s["total"]) == 31000.0


async def test_calculate_invalid_period(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": refs["employee_id"],
            "period_start": "2026-05-31",
            "period_end": "2026-05-01",
        },
        headers=headers,
    )
    assert r.status_code == 400


async def test_calculate_unknown_employee(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": 99999,
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Pay
# ---------------------------------------------------------------------------
async def test_pay_salary_creates_cashflow_expense(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    await _seed_system_salary_category(client, headers)

    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": refs["employee_id"],
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers=headers,
    )
    sid = r.json()["id"]
    total = float(r.json()["total"])

    r = await client.post(
        f"/api/v1/salary/{sid}/pay?account_id={refs['account_id']}", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"
    assert r.json()["paid_at"] is not None

    # Баланс счёта уменьшился на total.
    r = await client.get(f"/api/v1/cashflow/accounts/{refs['account_id']}", headers=headers)
    assert float(r.json()["current_balance"]) == 100000.0 - total


async def test_pay_already_paid_returns_400(client):
    refs = await _setup_full(client)
    headers = refs["headers"]
    r = await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": refs["employee_id"],
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers=headers,
    )
    sid = r.json()["id"]
    await client.post(f"/api/v1/salary/{sid}/pay", headers=headers)
    r = await client.post(f"/api/v1/salary/{sid}/pay", headers=headers)
    assert r.status_code == 400


async def test_isolation_between_tenants(client):
    refs_a = await _setup_full(client, TENANT_ALPHA)
    refs_b = await _setup_full(client, TENANT_BETA)
    h_a = refs_a["headers"]
    h_b = refs_b["headers"]

    await client.post(
        "/api/v1/salary/calculate",
        json={
            "employee_id": refs_a["employee_id"],
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        headers=h_a,
    )
    r_a = await client.get("/api/v1/salary/", headers=h_a)
    r_b = await client.get("/api/v1/salary/", headers=h_b)
    assert len(r_a.json()) == 1
    assert len(r_b.json()) == 0
