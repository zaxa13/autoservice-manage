"""Поставщики — async CRUD на shared-DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.supplier import Supplier
from app.schemas.responses import ErrorResponse
from app.schemas.supplier import (
    Supplier as SupplierSchema,
    SupplierCreate,
    SupplierUpdate,
)

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Поставщик не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get("/", response_model=list[SupplierSchema], responses=_auth)
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> list[SupplierSchema]:
    result = await db.execute(
        select(Supplier).order_by(Supplier.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get(
    "/{supplier_id}",
    response_model=SupplierSchema,
    responses={**_auth, **_404},
)
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
) -> SupplierSchema:
    s = await db.get(Supplier, (claims.tenant_id, supplier_id))
    if s is None:
        raise NotFoundException("Поставщик не найден")
    return s


@router.post(
    "/",
    response_model=SupplierSchema,
    status_code=status.HTTP_201_CREATED,
    responses=_write,
)
async def create_supplier(
    body: SupplierCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> SupplierSchema:
    s = Supplier(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


@router.put(
    "/{supplier_id}",
    response_model=SupplierSchema,
    responses={**_write, **_404},
)
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> SupplierSchema:
    s = await db.get(Supplier, (claims.tenant_id, supplier_id))
    if s is None:
        raise NotFoundException("Поставщик не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await db.flush()
    await db.refresh(s)
    return s


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_write, **_404},
)
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> Response:
    s = await db.get(Supplier, (claims.tenant_id, supplier_id))
    if s is None:
        raise NotFoundException("Поставщик не найден")
    await db.delete(s)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
