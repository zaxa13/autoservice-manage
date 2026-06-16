"""Учёт активных сессий тенанта и enforcement лимита по тарифу (Фаза 1).

Лимит — seat-based на ВЕСЬ тенант, источник правды: cross-schema чтение
`platform.tariff_plans.limits->>'max_sessions'` по текущему `platform.tenants.plan`
(обе схемы в одной БД `autoworks`, у роли tenant_app есть SELECT на platform.*).

Все запросы идут внутри `tenant_session(tenant_id)` — RLS уже ограничивает
app.user_sessions нужным тенантом, поэтому tenant_id в WHERE не дублируем.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


class SessionLimitReached(Exception):
    """Превышен лимит одновременных сессий тенанта (→ HTTP 409)."""

    def __init__(self, limit: int, current: int, plan: str | None):
        self.limit = limit
        self.current = current
        self.plan = plan
        super().__init__(f"session limit reached: {current}/{limit} (plan={plan})")


async def _read_plan_limit(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[str | None, int]:
    """Возвращает (plan_code, max_sessions). Дефолт — DEFAULT_MAX_SESSIONS, если
    плана/лимита нет (fail-safe в сторону базового тарифа)."""
    row = (
        await db.execute(
            text(
                "SELECT lower(t.plan) AS plan, (tp.limits->>'max_sessions')::int AS max_sessions "
                "FROM platform.tenants t "
                "LEFT JOIN platform.tariff_plans tp ON tp.code = lower(t.plan) "
                "WHERE t.id = :tid"
            ),
            {"tid": str(tenant_id)},
        )
    ).first()
    if row is None:
        return None, settings.DEFAULT_MAX_SESSIONS
    limit = row.max_sessions if row.max_sessions is not None else settings.DEFAULT_MAX_SESSIONS
    return row.plan, int(limit)


async def _count_active(db: AsyncSession) -> int:
    return (
        await db.execute(
            text(
                "SELECT count(*) FROM app.user_sessions "
                "WHERE revoked_at IS NULL "
                "  AND expires_at > now() "
                "  AND last_seen_at > now() - make_interval(mins => :idle)"
            ),
            {"idle": settings.SESSION_IDLE_MINUTES},
        )
    ).scalar_one()


async def enforce_and_create(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: int,
    jti: str,
    expires_at: datetime,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Проверяет лимит и создаёт строку сессии. Бросает SessionLimitReached.

    Атомарность гонки одновременных логинов — advisory-lock на tenant_id
    в рамках текущей транзакции: параллельные входы сериализуются."""
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": str(tenant_id)},
    )
    plan, limit = await _read_plan_limit(db, tenant_id)
    active = await _count_active(db)
    if active >= limit:
        raise SessionLimitReached(limit=limit, current=active, plan=plan)

    await db.execute(
        text(
            "INSERT INTO app.user_sessions "
            "  (tenant_id, user_id, jti, ip_address, user_agent, login_at, last_seen_at, expires_at) "
            "VALUES (:tid, :uid, :jti, :ip, :ua, now(), now(), :exp)"
        ),
        {
            "tid": str(tenant_id),
            "uid": user_id,
            "jti": jti,
            "ip": ip_address,
            "ua": (user_agent or "")[:400] or None,
            "exp": expires_at,
        },
    )


async def touch(db: AsyncSession, jti: str) -> None:
    """Лениво обновляет last_seen_at (троттлинг ~1/мин). Best-effort —
    вызывающий глушит ошибки, чтобы не ронять запрос."""
    await db.execute(
        text(
            "UPDATE app.user_sessions SET last_seen_at = now() "
            "WHERE jti = :jti AND revoked_at IS NULL "
            "  AND last_seen_at < now() - interval '60 seconds'"
        ),
        {"jti": jti},
    )


async def revoke(db: AsyncSession, jti: str, reason: str = "logout") -> None:
    await db.execute(
        text(
            "UPDATE app.user_sessions SET revoked_at = now(), revoked_reason = :r "
            "WHERE jti = :jti AND revoked_at IS NULL"
        ),
        {"jti": jti, "r": reason[:40]},
    )


def new_jti() -> str:
    return uuid.uuid4().hex


def default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
