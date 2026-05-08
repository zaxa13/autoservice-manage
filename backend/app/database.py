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
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Re-export Base — чтобы импортировать как `from app.database import Base`.
from app.models._base import Base  # noqa: F401

# Один engine на процесс. echo выключаем по умолчанию — DEBUG отдельно.
_runtime_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

_session_factory = async_sessionmaker(
    _runtime_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def tenant_session(tenant_id: UUID) -> AsyncIterator[AsyncSession]:
    """Открывает async-сессию с RLS-контекстом для tenant_id.

    Транзакция стартует автоматически и коммитится по выходу. Внутри
    можно делать вложенные SAVEPOINTs через `session.begin_nested()`.
    """
    async with _session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            yield session


async def dispose_engine() -> None:
    """Корректное закрытие пула соединений (вызывать в FastAPI lifespan)."""
    await _runtime_engine.dispose()
