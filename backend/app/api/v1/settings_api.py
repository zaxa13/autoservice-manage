"""Настройки тенанта — KV-store."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.setting import Setting
from app.schemas.responses import ErrorResponse, RevenuePlanResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Реквизиты организации (выводятся в шапке PDF-документов).
# ---------------------------------------------------------------------------
_COMPANY_KEYS = ("company_name", "company_address", "company_phone", "company_inn")


class CompanySettings(BaseModel):
    company_name: Optional[str] = Field(None, max_length=500)
    company_address: Optional[str] = Field(None, max_length=500)
    company_phone: Optional[str] = Field(None, max_length=100)
    company_inn: Optional[str] = Field(None, max_length=20)


@router.get(
    "/company",
    response_model=CompanySettings,
    responses={401: {"model": ErrorResponse}},
)
async def get_company_settings(
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    rows = (await db.execute(
        select(Setting).where(Setting.key.in_(_COMPANY_KEYS))
    )).scalars().all()
    by_key = {r.key: r.value for r in rows}
    return CompanySettings(**{k: by_key.get(k) for k in _COMPANY_KEYS})


@router.put(
    "/company",
    response_model=CompanySettings,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def set_company_settings(
    body: CompanySettings,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    payload = body.model_dump()
    for key in _COMPANY_KEYS:
        value = (payload.get(key) or "").strip() or None
        existing = await db.get(Setting, (claims.tenant_id, key))
        if value is None:
            if existing is not None:
                await db.delete(existing)
        else:
            if existing is None:
                db.add(Setting(tenant_id=claims.tenant_id, key=key, value=value))
            else:
                existing.value = value
    await db.flush()
    rows = (await db.execute(
        select(Setting).where(Setting.key.in_(_COMPANY_KEYS))
    )).scalars().all()
    by_key = {r.key: r.value for r in rows}
    return CompanySettings(**{k: by_key.get(k) for k in _COMPANY_KEYS})


class RevenuePlanIn(BaseModel):
    year: int = Field(..., ge=2020, le=2099)
    month: int = Field(..., ge=1, le=12)
    amount: float = Field(..., ge=0)


def _key(year: int, month: int) -> str:
    return f"revenue_plan_{year}_{month:02d}"


@router.get(
    "/revenue-plan",
    response_model=RevenuePlanResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_revenue_plan(
    year: int = Query(..., ge=2020, le=2099),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    row = await db.get(Setting, (claims.tenant_id, _key(year, month)))
    return {"year": year, "month": month, "amount": float(row.value) if row else None}


@router.put(
    "/revenue-plan",
    response_model=RevenuePlanResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def set_revenue_plan(
    body: RevenuePlanIn,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    pk = (claims.tenant_id, _key(body.year, body.month))
    row = await db.get(Setting, pk)
    if row:
        row.value = str(body.amount)
    else:
        db.add(
            Setting(
                tenant_id=claims.tenant_id,
                key=_key(body.year, body.month),
                value=str(body.amount),
            )
        )
    await db.flush()
    return {"year": body.year, "month": body.month, "amount": body.amount}
