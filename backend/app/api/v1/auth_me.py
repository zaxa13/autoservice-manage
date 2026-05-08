"""Минимальный auth-роутер для tenant-app.

В shared-DB архитектуре JWT выдаёт platform-api (или dedicated login
flow в Фазе 4-5). Tenant-app только декодирует токен и отдаёт claims —
этого достаточно для фронта чтобы отрисовать "вы вошли как X".

Полный legacy `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`
из старой версии будет вычеркнут или перенесён в platform-api в Фазе 4.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import TenantClaims
from app.dependencies import get_current_claims

router = APIRouter()


@router.get(
    "/me",
    response_model=TenantClaims,
    summary="Текущие claims из JWT",
    description=(
        "Возвращает декодированные claims токена: tenant_id, owner_id, "
        "user_id, roles. Не лезет в БД — чистый JWT."
    ),
)
def me(claims: TenantClaims = Depends(get_current_claims)) -> TenantClaims:
    return claims
