"""Запчасти — async CRUD на shared-DB.

Каждая запчасть в API-ответе обогащается `stock_quantity` из
`warehouse_items` (LEFT JOIN). RLS отфильтрует только данные текущего
тенанта.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.part import Part
from app.models.warehouse import WarehouseItem
from app.schemas.part import Part as PartSchema, PartCreate, PartUpdate
from app.schemas.responses import ErrorResponse

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Запчасть не найдена"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


def _to_dict(part: Part, stock: int) -> dict:
    return {
        "id": part.id,
        "name": part.name,
        "part_number": part.part_number,
        "brand": part.brand,
        "price": part.price,
        "purchase_price_last": part.purchase_price_last,
        "unit": part.unit,
        "category": part.category,
        "stock_quantity": stock,
    }


async def _enrich(parts: list[Part], db: AsyncSession) -> list[dict]:
    if not parts:
        return []
    ids = [p.id for p in parts]
    result = await db.execute(
        select(WarehouseItem.part_id, WarehouseItem.quantity)
        .where(WarehouseItem.part_id.in_(ids))
    )
    stock_map: dict[int, int] = {pid: int(q) for pid, q in result.all()}
    return [_to_dict(p, stock_map.get(p.id, 0)) for p in parts]


@router.get("/", response_model=list[PartSchema], responses=_auth)
async def list_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Нечёткий поиск по part_number"),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    stmt = select(Part).order_by(Part.id)
    if search and search.strip():
        term = search.strip().upper().replace(" ", "")
        stmt = stmt.where(Part.part_number.ilike(f"%{term}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return await _enrich(list(result.scalars().all()), db)


@router.get("/{part_id}", response_model=PartSchema, responses={**_auth, **_404})
async def get_part(
    part_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    part = await db.get(Part, (claims.tenant_id, part_id))
    if part is None:
        raise NotFoundException("Запчасть не найдена")
    enriched = await _enrich([part], db)
    return enriched[0]


@router.post(
    "/",
    response_model=PartSchema,
    status_code=status.HTTP_201_CREATED,
    responses=_write,
)
async def create_part(
    body: PartCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    part = Part(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(part)
    await db.flush()
    await db.refresh(part)
    enriched = await _enrich([part], db)
    return enriched[0]


@router.put("/{part_id}", response_model=PartSchema, responses={**_write, **_404})
async def update_part(
    part_id: int,
    body: PartUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    part = await db.get(Part, (claims.tenant_id, part_id))
    if part is None:
        raise NotFoundException("Запчасть не найдена")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(part, k, v)
    await db.flush()
    await db.refresh(part)
    enriched = await _enrich([part], db)
    return enriched[0]
