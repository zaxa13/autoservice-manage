"""Посты (колонки) для доски записей — async CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.appointment import Appointment
from app.models.appointment_post import AppointmentPost
from app.schemas.appointment_post import (
    AppointmentPost as AppointmentPostSchema,
    AppointmentPostCreate,
    AppointmentPostUpdate,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Пост не найден"}}
_409 = {409: {"model": ErrorResponse, "description": "Пост используется записями"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get("/", response_model=list[AppointmentPostSchema], responses=_auth)
async def list_posts(
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    result = await db.execute(
        select(AppointmentPost).order_by(AppointmentPost.sort_order, AppointmentPost.id)
    )
    return list(result.scalars().all())


@router.get(
    "/{post_id}",
    response_model=AppointmentPostSchema,
    responses={**_auth, **_404},
)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    p = await db.get(AppointmentPost, (claims.tenant_id, post_id))
    if p is None:
        raise NotFoundException("Пост не найден")
    return p


@router.post(
    "/",
    response_model=AppointmentPostSchema,
    status_code=status.HTTP_201_CREATED,
    responses=_write,
)
async def create_post(
    body: AppointmentPostCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    p = AppointmentPost(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return p


@router.put(
    "/{post_id}",
    response_model=AppointmentPostSchema,
    responses={**_write, **_404},
)
async def update_post(
    post_id: int,
    body: AppointmentPostUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    p = await db.get(AppointmentPost, (claims.tenant_id, post_id))
    if p is None:
        raise NotFoundException("Пост не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.flush()
    await db.refresh(p)
    return p


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_write, **_404, **_409},
)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> Response:
    p = await db.get(AppointmentPost, (claims.tenant_id, post_id))
    if p is None:
        raise NotFoundException("Пост не найден")

    appt_count = await db.scalar(
        select(func.count()).select_from(Appointment).where(
            Appointment.tenant_id == claims.tenant_id,
            Appointment.post_id == post_id,
        )
    )
    if appt_count:
        raise ConflictException(
            "Нельзя удалить пост с активными записями. "
            "Перетяните записи на другой пост и попробуйте снова."
        )

    await db.delete(p)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
