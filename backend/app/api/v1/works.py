"""Справочник видов работ — async CRUD на shared-DB."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.work import Work
from app.schemas.responses import ErrorResponse
from app.schemas.work import Work as WorkSchema, WorkCreate, WorkUpdate

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Вид работы не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get("/", response_model=list[WorkSchema], responses=_auth)
async def list_works(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Нечёткий поиск по названию"),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> list[WorkSchema]:
    stmt = select(Work).order_by(Work.id)
    if search:
        stmt = stmt.where(Work.name.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{work_id}", response_model=WorkSchema, responses={**_auth, **_404})
async def get_work(
    work_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
) -> WorkSchema:
    work = await db.get(Work, (claims.tenant_id, work_id))
    if work is None:
        raise NotFoundException("Вид работы не найден")
    return work


@router.post(
    "/",
    response_model=WorkSchema,
    status_code=status.HTTP_201_CREATED,
    responses=_write,
)
async def create_work(
    body: WorkCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> WorkSchema:
    work = Work(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(work)
    await db.flush()
    await db.refresh(work)
    return work


@router.put("/{work_id}", response_model=WorkSchema, responses={**_write, **_404})
async def update_work(
    work_id: int,
    body: WorkUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> WorkSchema:
    work = await db.get(Work, (claims.tenant_id, work_id))
    if work is None:
        raise NotFoundException("Вид работы не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(work, k, v)
    await db.flush()
    await db.refresh(work)
    return work
