"""Справочник марок и моделей автомобилей — глобальный read-only.

Наполняется alembic-миграцией. Tenant-app только читает.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.schemas.responses import ErrorResponse
from app.schemas.vehicle_brand import (
    BrandsListResponse,
    ModelsRequest,
    ModelsResponse,
)

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}


@router.get(
    "/",
    response_model=BrandsListResponse,
    summary="Список марок (глобальный справочник)",
    responses=_auth,
)
async def list_brands(
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    result = await db.execute(select(VehicleBrand).order_by(VehicleBrand.name))
    brands = list(result.scalars().all())
    return BrandsListResponse(brands=[{"id": b.id, "name": b.name} for b in brands])


@router.post(
    "/models",
    response_model=ModelsResponse,
    summary="Модели по марке",
    responses={
        **_auth,
        400: {"model": ErrorResponse, "description": "Не указан brand или brand_id"},
        404: {"model": ErrorResponse, "description": "Марка не найдена"},
    },
)
async def list_models(
    body: ModelsRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    if body.brand_id is not None:
        brand = await db.get(VehicleBrand, body.brand_id)
    elif body.brand and body.brand.strip():
        result = await db.execute(
            select(VehicleBrand).where(VehicleBrand.name.ilike(body.brand.strip()))
        )
        brand = result.scalar_one_or_none()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите brand или brand_id",
        )
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Марка не найдена"
        )
    result = await db.execute(
        select(VehicleModel).where(VehicleModel.brand_id == brand.id)
    )
    models = list(result.scalars().all())
    return ModelsResponse(models=[{"id": m.id, "name": m.name} for m in models])
