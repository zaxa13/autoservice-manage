"""Role-based авторизация через JWT-claims (без обращения к БД).

Источник истины — claim `roles` в JWT-токене, который выдаёт platform-api
(или внутренний логин tenant-app в Фазе 4-5). Сами роли — те же что
в `UserRole` в моделях:
- admin, manager, mechanic, accountant
"""
from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.core.security import TenantClaims
from app.dependencies import get_current_claims


def _check_roles(claims: TenantClaims, allowed: Iterable[str]) -> TenantClaims:
    allowed_set = set(allowed)
    if not (set(claims.roles) & allowed_set):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return claims


def require_admin(
    claims: TenantClaims = Depends(get_current_claims),
) -> TenantClaims:
    return _check_roles(claims, ["admin"])


def require_manager_or_admin(
    claims: TenantClaims = Depends(get_current_claims),
) -> TenantClaims:
    return _check_roles(claims, ["admin", "manager"])


def require_accountant_or_admin(
    claims: TenantClaims = Depends(get_current_claims),
) -> TenantClaims:
    return _check_roles(claims, ["admin", "accountant"])
