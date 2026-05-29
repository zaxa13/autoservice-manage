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
from app.models.part_brand import PartBrand
from app.models.warehouse import WarehouseItem
from app.schemas.part import Part as PartSchema, PartCreate, PartUpdate
from app.schemas.responses import ErrorResponse

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Запчасть не найдена"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


def _to_dict(part: Part, stock: int, brand_ref: PartBrand | None) -> dict:
    return {
        "id": part.id,
        "name": part.name,
        "part_number": part.part_number,
        "brand": part.brand,
        "brand_id": part.brand_id,
        "brand_ref": ({"id": brand_ref.id, "name": brand_ref.name} if brand_ref else None),
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

    brand_ids = {p.brand_id for p in parts if p.brand_id is not None}
    brand_map: dict[int, PartBrand] = {}
    if brand_ids:
        brand_rows = (
            await db.execute(select(PartBrand).where(PartBrand.id.in_(brand_ids)))
        ).scalars().all()
        brand_map = {b.id: b for b in brand_rows}

    return [
        _to_dict(p, stock_map.get(p.id, 0), brand_map.get(p.brand_id) if p.brand_id else None)
        for p in parts
    ]


async def _resolve_brand_text(db: AsyncSession, brand_id: int | None) -> str | None:
    """Денормализация — обновляем parts.brand текстом из справочника, чтобы
    legacy-код, читающий part.brand, видел актуальное имя."""
    if brand_id is None:
        return None
    brand = await db.get(PartBrand, brand_id)
    return brand.name if brand else None


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
    data = body.model_dump()
    # Если пришёл brand_id, синхронизируем legacy-текст с именем из справочника.
    if data.get("brand_id") is not None:
        name = await _resolve_brand_text(db, data["brand_id"])
        if name is None:
            raise NotFoundException("Бренд не найден")
        data["brand"] = name
    part = Part(tenant_id=claims.tenant_id, **data)
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
    patch = body.model_dump(exclude_unset=True)
    # brand_id меняется → синхронизируем legacy-текст. Сброс brand_id=None не
    # очищает brand-текст специально (пусть остаётся как заметка для пользователя).
    if "brand_id" in patch and patch["brand_id"] is not None:
        name = await _resolve_brand_text(db, patch["brand_id"])
        if name is None:
            raise NotFoundException("Бренд не найден")
        patch.setdefault("brand", name)
    for k, v in patch.items():
        setattr(part, k, v)
    await db.flush()
    await db.refresh(part)
    enriched = await _enrich([part], db)
    return enriched[0]
