"""TDD: JWT-декодер tenant-app.

Контракт `app.core.security.decode_tenant_token`:
- input: строка токена;
- success: возвращает `TenantClaims` pydantic-модель;
- fail: бросает `InvalidTokenError` с понятным сообщением.

Минимально валидный токен: `tenant_id` (UUID) + `exp` (unix ts), подписан
общим SECRET_KEY алгоритмом из ALGORITHM.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

from .conftest import TENANT_ALPHA, make_token


# Эти модули будут реализованы в Фазе 3 — пока что тесты упадут на ImportError.
pytest_plugins: list[str] = []


def _import_security():
    from app.core import security
    return security


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------
def test_decode_valid_token_returns_claims():
    sec = _import_security()
    token = make_token(tenant_id=TENANT_ALPHA, owner_id=uuid.uuid4())
    claims = sec.decode_tenant_token(token)
    assert claims.tenant_id == TENANT_ALPHA


def test_decode_token_carries_optional_claims():
    sec = _import_security()
    owner = uuid.uuid4()
    token = make_token(
        tenant_id=TENANT_ALPHA,
        owner_id=owner,
        user_id=42,
        roles=["admin", "manager"],
    )
    claims = sec.decode_tenant_token(token)
    assert claims.tenant_id == TENANT_ALPHA
    assert claims.owner_id == owner
    assert claims.user_id == 42
    assert claims.roles == ["admin", "manager"]


def test_decode_token_with_extra_claims_is_ignored():
    """Forward-compat: незнакомые поля не должны ломать декод."""
    sec = _import_security()
    token = make_token(
        tenant_id=TENANT_ALPHA,
        extra={"future_claim": "whatever", "feature_flag_x": True},
    )
    claims = sec.decode_tenant_token(token)
    assert claims.tenant_id == TENANT_ALPHA


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------
def test_decode_expired_token_raises(secret_key):
    sec = _import_security()
    token = make_token(tenant_id=TENANT_ALPHA, expires_in=timedelta(seconds=-10))
    with pytest.raises(sec.InvalidTokenError):
        sec.decode_tenant_token(token)


def test_decode_token_with_bad_signature_raises():
    sec = _import_security()
    bogus = "totally-different-secret-of-sufficient-length-12345"
    token = make_token(tenant_id=TENANT_ALPHA, secret=bogus)
    with pytest.raises(sec.InvalidTokenError):
        sec.decode_tenant_token(token)


def test_decode_garbage_string_raises():
    sec = _import_security()
    with pytest.raises(sec.InvalidTokenError):
        sec.decode_tenant_token("not.a.jwt")


def test_decode_token_without_tenant_id_raises(secret_key):
    """Минимально валидный токен обязан нести tenant_id."""
    sec = _import_security()
    token = jose_jwt.encode(
        {"owner_id": str(uuid.uuid4()), "exp": 9999999999},
        secret_key,
        algorithm="HS256",
    )
    with pytest.raises(sec.InvalidTokenError):
        sec.decode_tenant_token(token)


def test_decode_token_with_non_uuid_tenant_id_raises(secret_key):
    sec = _import_security()
    token = jose_jwt.encode(
        {"tenant_id": "not-a-uuid", "exp": 9999999999},
        secret_key,
        algorithm="HS256",
    )
    with pytest.raises(sec.InvalidTokenError):
        sec.decode_tenant_token(token)


# ---------------------------------------------------------------------------
# Pydantic claims model
# ---------------------------------------------------------------------------
def test_tenant_claims_is_pydantic_model():
    sec = _import_security()
    claims = sec.TenantClaims(tenant_id=TENANT_ALPHA)
    assert claims.tenant_id == TENANT_ALPHA
    # tenant_id должен быть единственным required-полем
    assert claims.owner_id is None
    assert claims.user_id is None
    assert claims.roles == []
