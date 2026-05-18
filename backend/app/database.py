"""Async-engine и tenant-aware session factory.

Любая работа с бизнес-таблицами (схема `app`) в рантайме идёт через
`tenant_session(tenant_id)` — он:

1. Открывает AsyncSession под ролью `tenant_app` (NOBYPASSRLS).
2. Стартует транзакцию.
3. Выполняет `SET LOCAL app.tenant_id = '<uuid>'`.

После выхода из контекст-менеджера транзакция коммитится (или откатывается
при исключении), GUC сбрасывается. Соединение возвращается в pool —
следующий запрос уже без `tenant_id`, RLS будет fail-closed (`NULL`).
"""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# Re-export Base — чтобы импортировать как `from app.database import Base`.
from app.models._base import Base  # noqa: F401

# Engine конфигурируем под PgBouncer в **transaction-pool**:
#
# 1. NullPool — не пуллим в SQLAlchemy, пуллит pgbouncer. Двойной pool
#    приводит к stale соединениям и привязке к event-loop в тестах.
#
# 2. statement_cache_size=0 + prepared_statement_cache_size=0 — asyncpg по
#    умолчанию кеширует prepared statements server-side. В transaction-mode
#    каждая транзакция может пойти на новое физическое соединение, и кеш
#    становится протухшим → "prepared statement does not exist".
#    См. https://magicstack.github.io/asyncpg/current/faq.html#why-am-i-getting-prepared-statement-errors
_runtime_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

_session_factory = async_sessionmaker(
    _runtime_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def auth_session() -> AsyncIterator[AsyncSession]:
    """Async-сессия без RLS-контекста (`app.tenant_id` не выставлен).

    Нужна **только** для login-эндпоинта, где tenant_id ещё неизвестен и
    мы зовём SECURITY DEFINER функцию `app.lookup_user_for_login(email)`
    — она сама обходит RLS внутри. Любые прямые SELECT по `app.*` через
    эту сессию упрутся в RLS (`tenant_id IS NULL` policy fail-closed).
    """
    async with _session_factory() as session:
        async with session.begin():
            yield session


@asynccontextmanager
async def tenant_session(tenant_id: UUID) -> AsyncIterator[AsyncSession]:
    """Открывает async-сессию с RLS-контекстом для tenant_id.

    Транзакция стартует автоматически и коммитится по выходу. Внутри
    можно делать вложенные SAVEPOINTs через `session.begin_nested()`.
    """
    async with _session_factory() as session:
        async with session.begin():
            # `SET LOCAL = $1` Postgres не принимает (это конфиг-команда, не
            # запрос). Используем функцию `set_config(name, value, is_local)`
            # — она принимает параметры и эквивалентна `SET LOCAL` при
            # is_local=true.
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            yield session


async def dispose_engine() -> None:
    """Корректное закрытие пула соединений (вызывать в FastAPI lifespan)."""
    await _runtime_engine.dispose()


# ---------------------------------------------------------------------------
# Sync tenant session — для sync-only сервисов (xhtml2pdf и т.п.), которые
# нельзя дёргать из async-кода без потери совместимости. Не пуллим, NullPool —
# каждый запрос отдельное соединение через pgbouncer.
# ---------------------------------------------------------------------------
_sync_runtime_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
_sync_engine = create_engine(_sync_runtime_url, poolclass=NullPool, future=True)
_sync_session_factory = sessionmaker(_sync_engine, expire_on_commit=False)


@contextmanager
def sync_tenant_session(tenant_id: UUID) -> Iterator[Session]:
    """Sync-сессия под `tenant_app` с выставленным `app.tenant_id` GUC.

    Используется только из sync-кода (PDF-генерация). Из async-эндпоинтов
    вызывать через `fastapi.concurrency.run_in_threadpool` или asyncio.to_thread.
    """
    session = _sync_session_factory()
    try:
        with session.begin():
            session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            yield session
    finally:
        session.close()
