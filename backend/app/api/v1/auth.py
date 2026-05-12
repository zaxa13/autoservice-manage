"""Auth-роутер tenant-app.

- `POST /login` — email + password → JWT с TenantClaims (tenant_id
  определяется по найденному app.users row). Внутри зовёт SECURITY
  DEFINER функцию `app.lookup_user_for_login`, которая обходит RLS на
  app.users (на login мы ещё не знаем tenant_id).
- `GET /me` — возвращает профиль текущего пользователя из БД (читает
  app.users под RLS, tenant_id уже выставлен в `get_tenant_db`).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TenantClaims,
    create_tenant_token,
    verify_password,
)
from app.database import auth_session
from app.dependencies import get_current_claims, get_tenant_db
from app.schemas.user import User as UserSchema

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Логин: email + password → JWT с tenant_id",
)
async def login(body: LoginRequest) -> TokenResponse:
    async with auth_session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT user_id, tenant_id, password_hash, role, is_active "
                    "FROM app.lookup_user_for_login(:email)"
                ),
                {"email": body.email},
            )
        ).first()

    if row is None or not verify_password(body.password, row.password_hash):
        # 401 одинаковый и для unknown email, и для wrong password —
        # не подсказываем перебиральщикам, какая часть неверна.
        logger.info("login failed: email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not row.is_active:
        logger.info("login blocked (inactive): email=%s user_id=%s", body.email, row.user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись неактивна",
        )

    token = create_tenant_token(
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        role=row.role,
        sub=body.email,
    )
    logger.info(
        "login ok: email=%s tenant_id=%s user_id=%s role=%s",
        body.email, row.tenant_id, row.user_id, row.role,
    )
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Профиль текущего пользователя",
)
async def me(
    claims: TenantClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserSchema:
    if claims.user_id is None:
        # Сюда может прийти owner-токен от platform-api (там user_id нет).
        # Для tenant-app это пока невалидный кейс.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не содержит user_id",
        )

    row = (
        await db.execute(
            text(
                "SELECT id, username, email, role, employee_id, is_active, "
                "password_must_be_changed, created_at, updated_at "
                "FROM app.users WHERE id = :uid"
            ),
            {"uid": claims.user_id},
        )
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return UserSchema(**dict(row))
