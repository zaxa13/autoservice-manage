"""Пользователи (учётки сотрудников) — admin-only CRUD + reset-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_admin
from app.core.security import TenantClaims, get_password_hash
from app.dependencies import get_tenant_db
from app.models.user import User
from app.schemas.responses import ErrorResponse, MessageResponse
from app.schemas.user import ResetPasswordRequest, User as UserSchema, UserUpdate

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Пользователь не найден"}}
_admin = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Только для администратора"},
}


@router.get("/", response_model=list[UserSchema], responses=_admin)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(require_admin),
):
    result = await db.execute(
        select(User).order_by(User.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserSchema, responses={**_admin, **_404})
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    u = await db.get(User, (claims.tenant_id, user_id))
    if u is None:
        raise NotFoundException("Пользователь не найден")
    return u


@router.put("/{user_id}", response_model=UserSchema, responses={**_admin, **_404})
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    u = await db.get(User, (claims.tenant_id, user_id))
    if u is None:
        raise NotFoundException("Пользователь не найден")

    data = body.model_dump(exclude_unset=True)
    if "password" in data and data["password"] is not None:
        u.password_hash = get_password_hash(data.pop("password"))
    if "role" in data and hasattr(data["role"], "value"):
        data["role"] = data["role"].value
    for k, v in data.items():
        setattr(u, k, v)
    await db.flush()
    await db.refresh(u)
    return u


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    responses={**_admin, **_404},
)
async def reset_user_password(
    user_id: int,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    u = await db.get(User, (claims.tenant_id, user_id))
    if u is None:
        raise NotFoundException("Пользователь не найден")
    u.password_hash = get_password_hash(body.new_password)
    u.password_must_be_changed = True
    await db.flush()
    return {"message": "Пароль сброшен. Пользователь должен сменить его при следующем входе."}
