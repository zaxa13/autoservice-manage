"""FastAPI-зависимости tenant-app.

`get_tenant_db` — единственная допустимая точка входа в БД для бизнес-роутов.
Прямой импорт `_session_factory` из `app.database` запрещён код-ревью.

Цепочка: HTTP-запрос → bearer-токен → `get_current_claims` → `TenantClaims`
→ `tenant_session(tenant_id)` → AsyncSession с открытой транзакцией и
установленным `app.tenant_id`.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import InvalidTokenError, TenantClaims, decode_tenant_token
from app.database import tenant_session
from app.services import session_service

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TenantClaims:
    """Извлекает и валидирует JWT из Authorization: Bearer."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_tenant_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_tenant_db(
    claims: TenantClaims = Depends(get_current_claims),
) -> AsyncIterator[AsyncSession]:
    """Async-сессия с RLS-контекстом для tenant из JWT."""
    async with tenant_session(claims.tenant_id) as session:
        # Лениво освежаем last_seen сессии (учёт лимита). Best-effort —
        # ошибка не должна ронять запрос. Троттлинг — внутри SQL (1/мин).
        if settings.SESSION_LIMIT_ENABLED and claims.jti:
            try:
                await session_service.touch(session, claims.jti)
            except Exception:  # noqa: BLE001
                logger.debug("session touch failed (ignored)", exc_info=True)
        yield session
