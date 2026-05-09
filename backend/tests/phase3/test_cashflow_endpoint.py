"""End-to-end тесты /api/v1/cashflow."""
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


async def _seed_account(client, headers, name: str = "Касса", initial: float = 0) -> int:
    r = await client.post(
        "/api/v1/cashflow/accounts",
        json={"name": name, "account_type": "cash", "initial_balance": str(initial)},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_category(client, headers, name: str, ttype: str = "income") -> int:
    r = await client.post(
        "/api/v1/cashflow/categories",
        json={"name": name, "transaction_type": ttype},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def test_list_accounts_requires_role(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["mechanic"])
    r = await client.get(
        "/api/v1/cashflow/accounts", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_accountant_can_list_accounts(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["accountant"])
    r = await client.get(
        "/api/v1/cashflow/accounts", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


async def test_create_account_requires_admin(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["accountant"])
    r = await client.post(
        "/api/v1/cashflow/accounts",
        json={"name": "Касса", "account_type": "cash", "initial_balance": "100"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
async def test_account_balance_starts_at_initial(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса", initial=1000)
    r = await client.get(f"/api/v1/cashflow/accounts/{aid}", headers=headers)
    assert r.status_code == 200
    assert float(r.json()["current_balance"]) == 1000.0


async def test_delete_account_with_history_returns_400(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers)
    cat = await _seed_category(client, headers, "Прочий доход", "income")
    r = await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "income",
            "account_id": aid,
            "category_id": cat,
            "amount": "100",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = await client.delete(f"/api/v1/cashflow/accounts/{aid}", headers=headers)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
async def test_filter_categories_by_type(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_category(client, headers, "Доход X", "income")
    await _seed_category(client, headers, "Расход X", "expense")
    r = await client.get(
        "/api/v1/cashflow/categories?transaction_type=income", headers=headers
    )
    types = {c["transaction_type"] for c in r.json()}
    assert types == {"income"}


# ---------------------------------------------------------------------------
# Transactions: income / expense / transfer
# ---------------------------------------------------------------------------
async def test_income_increases_balance(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса", initial=500)
    cat = await _seed_category(client, headers, "Прочий доход", "income")
    await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "income",
            "account_id": aid,
            "category_id": cat,
            "amount": "300",
        },
        headers=headers,
    )
    r = await client.get(f"/api/v1/cashflow/accounts/{aid}", headers=headers)
    assert float(r.json()["current_balance"]) == 800.0


async def test_expense_decreases_balance(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса", initial=1000)
    cat = await _seed_category(client, headers, "Аренда", "expense")
    await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "expense",
            "account_id": aid,
            "category_id": cat,
            "amount": "250",
        },
        headers=headers,
    )
    r = await client.get(f"/api/v1/cashflow/accounts/{aid}", headers=headers)
    assert float(r.json()["current_balance"]) == 750.0


async def test_transfer_moves_balance_between_accounts(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    a_from = await _seed_account(client, headers, "Касса", initial=1000)
    a_to = await _seed_account(client, headers, "Банк", initial=0)
    cat = await _seed_category(client, headers, "Перевод", "transfer")
    r = await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "transfer",
            "account_id": a_from,
            "to_account_id": a_to,
            "category_id": cat,
            "amount": "400",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = await client.get(f"/api/v1/cashflow/accounts/{a_from}", headers=headers)
    assert float(r.json()["current_balance"]) == 600.0
    r = await client.get(f"/api/v1/cashflow/accounts/{a_to}", headers=headers)
    assert float(r.json()["current_balance"]) == 400.0


async def test_transfer_without_to_account_returns_400(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса", initial=1000)
    cat = await _seed_category(client, headers, "Перевод", "transfer")
    r = await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "transfer",
            "account_id": aid,
            "category_id": cat,
            "amount": "100",
        },
        headers=headers,
    )
    assert r.status_code == 400


async def test_category_type_mismatch_returns_400(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса")
    cat_expense = await _seed_category(client, headers, "Расход", "expense")
    r = await client.post(
        "/api/v1/cashflow/transactions",
        json={
            "transaction_type": "income",  # ≠ expense category
            "account_id": aid,
            "category_id": cat_expense,
            "amount": "100",
        },
        headers=headers,
    )
    assert r.status_code == 400


async def test_transactions_filter_by_account(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    a1 = await _seed_account(client, headers, "Касса 1")
    a2 = await _seed_account(client, headers, "Касса 2")
    cat = await _seed_category(client, headers, "Прочий доход", "income")
    for aid in (a1, a1, a2):
        await client.post(
            "/api/v1/cashflow/transactions",
            json={
                "transaction_type": "income",
                "account_id": aid,
                "category_id": cat,
                "amount": "100",
            },
            headers=headers,
        )
    r = await client.get(
        f"/api/v1/cashflow/transactions?account_id={a1}", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["total"] == 2


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
async def test_summary_aggregates_income_and_expense(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    aid = await _seed_account(client, headers, "Касса", initial=1000)
    cat_in = await _seed_category(client, headers, "Доход", "income")
    cat_out = await _seed_category(client, headers, "Расход", "expense")
    await client.post("/api/v1/cashflow/transactions", json={
        "transaction_type": "income", "account_id": aid, "category_id": cat_in, "amount": "300"
    }, headers=headers)
    await client.post("/api/v1/cashflow/transactions", json={
        "transaction_type": "expense", "account_id": aid, "category_id": cat_out, "amount": "100"
    }, headers=headers)

    r = await client.get("/api/v1/cashflow/summary", headers=headers)
    assert r.status_code == 200
    s = r.json()
    assert float(s["total_income"]) == 300.0
    assert float(s["total_expense"]) == 100.0
    assert float(s["net_flow"]) == 200.0
    assert float(s["total_balance"]) == 1200.0  # 1000 + 300 - 100


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    h_a = {"Authorization": f"Bearer {t_a}"}
    h_b = {"Authorization": f"Bearer {t_b}"}
    await _seed_account(client, h_a, "Alpha-cash")
    await _seed_account(client, h_b, "Beta-cash")
    r_a = await client.get("/api/v1/cashflow/accounts", headers=h_a)
    r_b = await client.get("/api/v1/cashflow/accounts", headers=h_b)
    assert {a["name"] for a in r_a.json()} == {"Alpha-cash"}
    assert {a["name"] for a in r_b.json()} == {"Beta-cash"}
