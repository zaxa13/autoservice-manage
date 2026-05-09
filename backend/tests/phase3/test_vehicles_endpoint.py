"""End-to-end тесты /api/v1/vehicles."""
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


async def _setup_refs(client, headers) -> dict:
    """Создаёт customer + brand + model для тенанта владельца token."""
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Vehicle Owner", "phone": "+79000000000"},
        headers=headers,
    )
    cid = r.json()["id"]

    r = await client.post(
        "/api/v1/vehicle-brands/import",
        json={"brands": [{"name": "Toyota", "models": ["Camry", "Corolla"]}]},
        headers=headers,
    )
    assert r.status_code == 200

    r = await client.get("/api/v1/vehicle-brands/", headers=headers)
    bid = r.json()["brands"][0]["id"]

    r = await client.post(
        "/api/v1/vehicle-brands/models",
        json={"brand_id": bid},
        headers=headers,
    )
    mid = next(m["id"] for m in r.json()["models"] if m["name"] == "Camry")

    return {"customer_id": cid, "brand_id": bid, "model_id": mid}


def _vehicle_payload(refs: dict, **kw) -> dict:
    base = {
        "license_plate": "А001АА777",
        "year": 2020,
        "mileage": 50000,
        **refs,
    }
    base.update(kw)
    return base


async def test_list_without_auth_returns_401(client):
    r = await client.get("/api/v1/vehicles/")
    assert r.status_code == 401


async def test_create_validates_customer(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    refs = await _setup_refs(client, headers)
    bad = {**_vehicle_payload(refs), "customer_id": 99999}
    r = await client.post("/api/v1/vehicles/", json=bad, headers=headers)
    assert r.status_code == 404


async def test_create_validates_model_belongs_to_brand(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    refs = await _setup_refs(client, headers)
    # Создаём вторую марку с моделью, и пытаемся использовать чужую модель
    await client.post(
        "/api/v1/vehicle-brands/import",
        json={
            "brands": [
                {"name": "Toyota", "models": ["Camry"]},
                {"name": "BMW", "models": ["X5"]},
            ]
        },
        headers=headers,
    )
    r = await client.get("/api/v1/vehicle-brands/", headers=headers)
    brands = {b["name"]: b["id"] for b in r.json()["brands"]}
    r = await client.post(
        "/api/v1/vehicle-brands/models",
        json={"brand_id": brands["BMW"]},
        headers=headers,
    )
    bmw_x5 = r.json()["models"][0]["id"]

    # У нас Toyota brand_id, но model_id = BMW X5 — должно упасть на 400
    r = await client.get("/api/v1/vehicle-brands/", headers=headers)
    toyota_id = brands["Toyota"]

    bad = _vehicle_payload(
        {"customer_id": refs["customer_id"], "brand_id": toyota_id, "model_id": bmw_x5}
    )
    r = await client.post("/api/v1/vehicles/", json=bad, headers=headers)
    assert r.status_code == 400


async def test_create_get_vehicle(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    refs = await _setup_refs(client, headers)

    r = await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs, vin="JT1234567890ABCDE"),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    assert r.json()["customer"]["full_name"] == "Vehicle Owner"
    assert r.json()["brand"]["name"] == "Toyota"
    assert r.json()["model"]["name"] == "Camry"

    r = await client.get(f"/api/v1/vehicles/{vid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["vin"] == "JT1234567890ABCDE"


async def test_list_filter_by_customer(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    refs = await _setup_refs(client, headers)

    # Второй customer
    r = await client.post(
        "/api/v1/customers/",
        json={"full_name": "Other", "phone": "+79991111111"},
        headers=headers,
    )
    other_id = r.json()["id"]

    await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs, license_plate="А001"),
        headers=headers,
    )
    refs2 = {**refs, "customer_id": other_id}
    await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs2, license_plate="Б002"),
        headers=headers,
    )

    r = await client.get(
        f"/api/v1/vehicles/?customer_id={refs['customer_id']}", headers=headers
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["license_plate"] == "А001"


async def test_search_by_license_plate(client):
    token = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    refs = await _setup_refs(client, headers)
    await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs, license_plate="А777ВВ"),
        headers=headers,
    )
    r = await client.get(
        "/api/v1/vehicles/search/by-license-plate?license_plate=777", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["license_plate"] == "А777ВВ"


async def test_isolation_between_tenants(client):
    t_a = make_token(tenant_id=TENANT_ALPHA, roles=["admin"])
    t_b = make_token(tenant_id=TENANT_BETA, roles=["admin"])
    refs_a = await _setup_refs(client, {"Authorization": f"Bearer {t_a}"})
    refs_b = await _setup_refs(client, {"Authorization": f"Bearer {t_b}"})

    await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs_a, license_plate="ALPHA-1"),
        headers={"Authorization": f"Bearer {t_a}"},
    )
    await client.post(
        "/api/v1/vehicles/", json=_vehicle_payload(refs_b, license_plate="BETA-1"),
        headers={"Authorization": f"Bearer {t_b}"},
    )

    r_a = await client.get(
        "/api/v1/vehicles/", headers={"Authorization": f"Bearer {t_a}"}
    )
    r_b = await client.get(
        "/api/v1/vehicles/", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert {v["license_plate"] for v in r_a.json()} == {"ALPHA-1"}
    assert {v["license_plate"] for v in r_b.json()} == {"BETA-1"}
