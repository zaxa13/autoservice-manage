"""Глобальный справочник брендов запчастей. Только чтение для тенант-приложения."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.part_brand import PartBrand
from app.schemas.part_brand import PartBrand as PartBrandSchema
from app.schemas.responses import ErrorResponse

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}


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
