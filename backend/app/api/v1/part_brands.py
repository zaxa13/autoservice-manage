"""Глобальный справочник брендов запчастей.

Append-only из приложения: GET доступен любому авторизованному, POST —
тоже (любой пользователь может добавить отсутствующий бренд прямо из
карточки запчасти). UPDATE/DELETE через приложение запрещены на уровне
БД-роли — каталог в этом смысле read-mostly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.part_brand import PartBrand
from app.schemas.part_brand import (
    PartBrand as PartBrandSchema,
    PartBrandCreate,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_conflict = {
    409: {"model": ErrorResponse, "description": "Бренд с таким именем уже есть"},
}


def _normalize_brand_name(raw: str) -> str:
    """Каноничный формат: trim, collapse spaces, заглавная буква в каждом слове.

    «mann» → «Mann», «MANN» → «Mann», «general ricambi» → «General Ricambi».
    Для строгих акронимов (KYB, NGK) пользователь увидит вариант с заглавной
    первой буквой — небольшая потеря, но единый канон важнее.
    """
    s = " ".join(raw.split())
    return " ".join(w[:1].upper() + w[1:].lower() for w in s.split(" "))


@router.get(
    "/",
    response_model=list[PartBrandSchema],
    summary="Список брендов запчастей",
    responses=_auth,
)
async def list_part_brands(
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> list[PartBrandSchema]:
    result = await db.execute(select(PartBrand).order_by(PartBrand.name))
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=PartBrandSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый бренд",
    responses={**_auth, **_conflict},
)
async def create_part_brand(
    body: PartBrandCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> PartBrandSchema:
    name = _normalize_brand_name(body.name)
    if not name:
        raise HTTPException(status_code=400, detail="Название бренда обязательно")

    existing = (
        await db.execute(
            select(PartBrand).where(func.lower(PartBrand.name) == name.lower()).limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_brand",
                "message": f"Бренд «{existing.name}» уже есть в справочнике",
                "existing_id": existing.id,
                "existing_name": existing.name,
            },
        )

    brand = PartBrand(name=name)
    db.add(brand)
    await db.flush()
    await db.refresh(brand)
    return brand
