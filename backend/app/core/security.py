"""JWT-утилиты tenant-app + bcrypt-хеширование паролей.

Two-mode JWT:
- Legacy `create_access_token` / `decode_access_token` — старый формат
  (только `sub` + `exp`), оставлены до Фазы 4 для обратной совместимости
  кода, который ещё не переписан.
- Новый `decode_tenant_token` → `TenantClaims` — формат shared-DB
  архитектуры, обязательно несёт `tenant_id` (UUID). Используется
  зависимостью `get_current_claims` в `app.dependencies`.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Passwords (legacy compat)
# ---------------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error("Password verification error: %s", e)
        return False


def get_password_hash(password: str) -> str:
    if not isinstance(password, str):
        password = str(password)
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


# ---------------------------------------------------------------------------
# Legacy JWT (оставлено до Фазы 4 — будет удалено вместе со старым auth flow)
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        logger.warning("JWT decode error: %s: %s", type(e).__name__, e)
        return None


# ---------------------------------------------------------------------------
# Shared-DB JWT
# ---------------------------------------------------------------------------
class TenantClaims(BaseModel):
    """Claims, извлекаемые из JWT для tenant-app.

    `tenant_id` — обязательный UUID. Остальное опционально: токены могут
    приходить от platform-api (owner-flow) или от внутреннего логина
    employee, у них разные подмножества полей.
    """

    tenant_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    user_id: int | None = None
    # employee_id — id связанного сотрудника в `app.employees`. Нужно для
    # роутов, которые принимают заказ-наряды от имени конкретного сотрудника.
    employee_id: int | None = None
    sub: str | None = None
    roles: list[str] = Field(default_factory=list)
    # jti — идентификатор сессии (учёт лимита сессий). Может отсутствовать
    # у старых токенов и owner-токенов от platform-api.
    jti: str | None = None

    model_config = {"extra": "ignore"}

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _coerce_tenant_id(cls, v):
        if isinstance(v, uuid.UUID):
            return v
        if isinstance(v, str):
            # pydantic сам поднимет ValidationError если строка не UUID
            return uuid.UUID(v)
        return v


class InvalidTokenError(Exception):
    """Брошен при любых проблемах с tenant-токеном: подпись, expiry,
    отсутствующие/невалидные claims."""


def create_tenant_token(
    *,
    tenant_id: uuid.UUID,
    user_id: int,
    role: str,
    sub: str,
    employee_id: int | None = None,
    jti: str | None = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Выпускает JWT с TenantClaims-совместимой нагрузкой.

    Используется login-эндпоинтом tenant-app после успешной аутентификации
    через `app.lookup_user_for_login`. `jti` — идентификатор сессии для
    учёта лимита одновременных сессий (если фича включена).
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict = {
        "sub": sub,
        "tenant_id": str(tenant_id),
        "user_id": user_id,
        "roles": [role],
        "exp": expire,
    }
    if employee_id is not None:
        payload["employee_id"] = employee_id
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_tenant_token(token: str) -> TenantClaims:
    """Декодирует и валидирует токен. Поднимает `InvalidTokenError`."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as e:
        raise InvalidTokenError(f"jwt: {e}") from e

    try:
        return TenantClaims(**payload)
    except (ValidationError, ValueError) as e:
        raise InvalidTokenError(f"claims: {e}") from e
