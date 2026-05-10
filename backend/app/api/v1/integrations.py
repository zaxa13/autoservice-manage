"""Внешние интеграции: ГИБДД + поставщики запчастей.

Все endpoint'ы — async, обращаются через `httpx.AsyncClient` (с
возможностью замены transport в тестах через `app.integrations._helpers`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_tenant_db
from app.integrations.gibdd import check_vehicle_gibdd
from app.integrations.parts_suppliers import create_supplier_order, search_parts
from app.schemas.responses import (
    ErrorResponse,
    IntegrationResponse,
    PartsSearchResponse,
    SupplierOrderRequest,
)

router = APIRouter()

_write = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Недостаточно прав"},
}


@router.get(
    "/gibdd/vehicle/{vin}",
    response_model=IntegrationResponse,
    responses=_write,
)
async def get_vehicle_info_gibdd(
    vin: str,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    result = await check_vehicle_gibdd(db, tenant_id=claims.tenant_id, vin=vin)
    if "error" in result:
        return IntegrationResponse(data=None, error=result["error"])
    return IntegrationResponse(data=result, error=None)


@router.get(
    "/suppliers/search",
    response_model=PartsSearchResponse,
    responses=_write,
)
async def search_parts_suppliers(
    query: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    result = await search_parts(db, tenant_id=claims.tenant_id, query=query)
    if "error" in result and "results" not in result:
        return PartsSearchResponse(results=[], error=result["error"])
    return PartsSearchResponse(
        results=result.get("results", []),
        error=result.get("error"),
    )


@router.post(
    "/suppliers/order",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, 400: {"model": ErrorResponse, "description": "Ошибка"}},
)
async def create_supplier_order_endpoint(
    body: SupplierOrderRequest,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    result = await create_supplier_order(
        db, tenant_id=claims.tenant_id, order_data=body.model_dump()
    )
    if "error" in result:
        return IntegrationResponse(data=None, error=result["error"])
    return IntegrationResponse(data=result, error=None)
