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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    TenantClaims,
    create_tenant_token,
    verify_password,
)
from app.database import auth_session, tenant_session
from app.dependencies import get_current_claims, get_tenant_db
from app.schemas.user import User as UserSchema
from app.services import session_service
from app.services.session_service import SessionLimitReached

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutOthersResponse(BaseModel):
    revoked: int


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Логин: email + password → JWT с tenant_id",
)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    async with auth_session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT user_id, tenant_id, password_hash, role, is_active, employee_id "
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

    # Лимит одновременных сессий на тенант (seat-based, по тарифу).
    jti = session_service.new_jti()
    expires_at = session_service.default_expires_at()
    if settings.SESSION_LIMIT_ENABLED:
        try:
            async with tenant_session(row.tenant_id) as db:
                await session_service.enforce_and_create(
                    db,
                    tenant_id=row.tenant_id,
                    user_id=row.user_id,
                    jti=jti,
                    expires_at=expires_at,
                    ip_address=_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                )
        except SessionLimitReached as exc:
            logger.info(
                "login blocked (session limit): tenant_id=%s %d/%d plan=%s",
                row.tenant_id, exc.current, exc.limit, exc.plan,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "session_limit_reached",
                    "message": "Достигнут лимит одновременных сессий по вашему тарифу.",
                    "limit": exc.limit,
                    "current": exc.current,
                    "plan": exc.plan,
                },
            )
        except Exception:
            # Любой непредвиденный сбой учёта сессий НЕ должен блокировать вход
            # (fail-open): хуже потерять enforcement, чем закрыть всем логин.
            logger.exception(
                "session enforcement failed (fail-open allow): tenant_id=%s", row.tenant_id
            )

    token = create_tenant_token(
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        role=row.role,
        sub=body.email,
        employee_id=row.employee_id,
        jti=jti,
    )
    logger.info(
        "login ok: email=%s tenant_id=%s user_id=%s role=%s",
        body.email, row.tenant_id, row.user_id, row.role,
    )
    return TokenResponse(access_token=token)


@router.post(
    "/logout-others",
    response_model=LogoutOthersResponse,
    status_code=status.HTTP_200_OK,
    summary="Снять свои активные сессии (аварийный выход с экрана лимита)",
)
async def logout_others(body: LoginRequest) -> LogoutOthersResponse:
    """Гасит ВСЕ активные сессии самого пользователя — освобождает слот,
    когда вход заблокирован лимитом из-за застрявшей сессии (закрытый
    браузер / другое устройство).

    На экране лимита пользователь ещё не авторизован, поэтому ручка
    повторно проверяет email+password (та же логика, что в /login) —
    нельзя выкинуть чужого, зная только email. Гасим строго свои сессии
    (по user_id); чужих в тенанте (на мульти-seat тарифах) не трогаем."""
    async with auth_session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT user_id, tenant_id, password_hash, is_active "
                    "FROM app.lookup_user_for_login(:email)"
                ),
                {"email": body.email},
            )
        ).first()

    if row is None or not verify_password(body.password, row.password_hash):
        logger.info("logout_others failed (bad creds): email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись неактивна",
        )

    async with tenant_session(row.tenant_id) as db:
        res = await db.execute(
            text(
                "UPDATE app.user_sessions SET revoked_at = now(), "
                "revoked_reason = 'logout_others' "
                "WHERE user_id = :uid AND revoked_at IS NULL"
            ),
            {"uid": row.user_id},
        )
        revoked = res.rowcount or 0

    logger.info(
        "logout_others: email=%s tenant_id=%s user_id=%s revoked=%d",
        body.email, row.tenant_id, row.user_id, revoked,
    )
    return LogoutOthersResponse(revoked=revoked)


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:45]
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()[:45]
    return request.client.host if request.client else None


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


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Выход: освобождает сессию (учёт лимита сессий)",
)
async def logout(
    claims: TenantClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Отзывает текущую сессию по jti — освобождает место под лимитом.
    Токен остаётся валидным до exp (stateless JWT), но место под лимитом
    освобождается сразу. Идемпотентно."""
    if claims.jti:
        await session_service.revoke(db, claims.jti, reason="logout")
    return {"ok": True}
