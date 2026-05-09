"""Транспортные средства — async CRUD c FK на customers/brands/models.

Без `joinedload`/`selectinload`, потому что Phase 2 модели не несут
relationships (composite FK создаёт нюансы — будем добавлять централизованно
в будущем). Вместо этого — bulk-fetch связанных сущностей по ids.

GET /{id}/history (история обслуживания) подключим в Wave 3 вместе с
миграцией orders.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.schemas.responses import ErrorResponse
from app.schemas.vehicle import (
    Vehicle as VehicleSchema,
    VehicleCreate,
    VehicleUpdate,
)

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Транспортное средство не найдено"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


def _vehicle_dict(v: Vehicle, customer, brand, model) -> dict:
    return {
        "id": v.id,
        "vin": v.vin,
        "license_plate": v.license_plate,
        "brand_id": v.brand_id,
        "model_id": v.model_id,
        "year": v.year,
        "mileage": v.mileage,
        "customer_id": v.customer_id,
        "created_at": v.created_at,
        "customer": customer,
        "brand": ({"id": brand.id, "name": brand.name} if brand else None),
        "model": ({"id": model.id, "name": model.name} if model else None),
    }


async def _serialize_one(
    db: AsyncSession, v: Vehicle, claims: TenantClaims
) -> dict:
    customer = await db.get(Customer, (claims.tenant_id, v.customer_id))
    brand = await db.get(VehicleBrand, (claims.tenant_id, v.brand_id))
    model = await db.get(VehicleModel, (claims.tenant_id, v.model_id))
    return _vehicle_dict(v, customer, brand, model)


async def _serialize_many(
    db: AsyncSession, vehicles: list[Vehicle]
) -> list[dict]:
    if not vehicles:
        return []
    cids = {v.customer_id for v in vehicles}
    bids = {v.brand_id for v in vehicles}
    mids = {v.model_id for v in vehicles}
    cmap = {
        c.id: c
        for c in (
            await db.execute(select(Customer).where(Customer.id.in_(cids)))
        ).scalars()
    }
    bmap = {
        b.id: b
        for b in (
            await db.execute(select(VehicleBrand).where(VehicleBrand.id.in_(bids)))
        ).scalars()
    }
    mmap = {
        m.id: m
        for m in (
            await db.execute(select(VehicleModel).where(VehicleModel.id.in_(mids)))
        ).scalars()
    }
    return [
        _vehicle_dict(v, cmap.get(v.customer_id), bmap.get(v.brand_id), mmap.get(v.model_id))
        for v in vehicles
    ]


@router.get("/", response_model=list[VehicleSchema], responses=_auth)
async def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    stmt = select(Vehicle).order_by(Vehicle.id)
    if customer_id is not None:
        stmt = stmt.where(Vehicle.customer_id == customer_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    vehicles = list(result.scalars().all())
    return await _serialize_many(db, vehicles)


@router.get(
    "/search/by-license-plate",
    response_model=VehicleSchema,
    responses={**_auth, **_404},
)
async def search_by_plate(
    license_plate: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    norm = license_plate.strip().upper().replace(" ", "")
    result = await db.execute(
        select(Vehicle).where(Vehicle.license_plate.ilike(f"%{norm}%")).limit(1)
    )
    v = result.scalar_one_or_none()
    if v is None:
        raise NotFoundException("Транспортное средство не найдено")
    return await _serialize_one(db, v, claims)


@router.get(
    "/search/by-vin",
    response_model=VehicleSchema,
    responses={**_auth, 400: {"model": ErrorResponse}, **_404},
)
async def search_by_vin(
    vin: str = Query(..., min_length=6, max_length=17),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    norm = vin.strip().upper()
    if len(norm) == 17:
        result = await db.execute(select(Vehicle).where(Vehicle.vin == norm).limit(1))
    elif len(norm) == 6:
        # PostgreSQL substr с -6 — последние 6 символов.
        from sqlalchemy import func
        result = await db.execute(
            select(Vehicle).where(func.substr(Vehicle.vin, -6) == norm).limit(1)
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="VIN должен быть 6 последних символов или полный 17-символьный",
        )
    v = result.scalar_one_or_none()
    if v is None:
        raise NotFoundException("Транспортное средство не найдено")
    return await _serialize_one(db, v, claims)


@router.get("/search", response_model=list[VehicleSchema], responses=_auth)
async def search_vehicles(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    norm = q.strip().upper().replace(" ", "")
    raw = q.strip().lower()

    # Phone match → customer ids → vehicles by customer_id.
    cust_rows = await db.execute(
        select(Customer.id).where(Customer.phone.ilike(f"%{raw}%"))
    )
    cust_ids = [row[0] for row in cust_rows.all()]

    conditions = [
        Vehicle.vin.ilike(f"%{norm}%"),
        Vehicle.license_plate.ilike(f"%{norm}%"),
    ]
    if cust_ids:
        conditions.append(Vehicle.customer_id.in_(cust_ids))

    result = await db.execute(
        select(Vehicle)
        .where(or_(*conditions))
        .order_by(Vehicle.id.desc())
        .limit(50)
    )
    vehicles = list(result.scalars().all())
    return await _serialize_many(db, vehicles)


@router.get("/{vehicle_id}", response_model=VehicleSchema, responses={**_auth, **_404})
async def get_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    v = await db.get(Vehicle, (claims.tenant_id, vehicle_id))
    if v is None:
        raise NotFoundException("Транспортное средство не найдено")
    return await _serialize_one(db, v, claims)


@router.post(
    "/",
    response_model=VehicleSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Модель не принадлежит марке"},
        404: {"model": ErrorResponse, "description": "Клиент / марка / модель не найдены"},
    },
)
async def create_vehicle(
    body: VehicleCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    customer = await db.get(Customer, (claims.tenant_id, body.customer_id))
    if customer is None:
        raise NotFoundException("Клиент не найден")
    brand = await db.get(VehicleBrand, (claims.tenant_id, body.brand_id))
    if brand is None:
        raise NotFoundException("Марка не найдена")
    model = await db.get(VehicleModel, (claims.tenant_id, body.model_id))
    if model is None:
        raise NotFoundException("Модель не найдена")
    if model.brand_id != brand.id:
        raise HTTPException(
            status_code=400, detail="Модель не принадлежит указанной марке"
        )

    v = Vehicle(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return await _serialize_one(db, v, claims)


@router.put(
    "/{vehicle_id}",
    response_model=VehicleSchema,
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Модель не принадлежит марке"},
        **_404,
    },
)
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    v = await db.get(Vehicle, (claims.tenant_id, vehicle_id))
    if v is None:
        raise NotFoundException("Транспортное средство не найдено")

    data = body.model_dump(exclude_unset=True)

    if "customer_id" in data:
        if await db.get(Customer, (claims.tenant_id, data["customer_id"])) is None:
            raise NotFoundException("Клиент не найден")

    new_brand_id = data.get("brand_id", v.brand_id)
    new_model_id = data.get("model_id", v.model_id)

    if "brand_id" in data:
        if await db.get(VehicleBrand, (claims.tenant_id, data["brand_id"])) is None:
            raise NotFoundException("Марка не найдена")
    if "model_id" in data:
        model = await db.get(VehicleModel, (claims.tenant_id, data["model_id"]))
        if model is None:
            raise NotFoundException("Модель не найдена")
        if model.brand_id != new_brand_id:
            raise HTTPException(
                status_code=400, detail="Модель не принадлежит указанной марке"
            )

    # Если сменили только brand_id, валидируем текущую model
    if "brand_id" in data and "model_id" not in data:
        current_model = await db.get(VehicleModel, (claims.tenant_id, v.model_id))
        if current_model is None or current_model.brand_id != new_brand_id:
            raise HTTPException(
                status_code=400,
                detail="Текущая модель не принадлежит новой марке — обновите model_id",
            )

    for k, val in data.items():
        setattr(v, k, val)
    await db.flush()
    await db.refresh(v)
    return await _serialize_one(db, v, claims)
