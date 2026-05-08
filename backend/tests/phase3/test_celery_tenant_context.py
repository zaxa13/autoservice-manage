"""TDD: Celery-декоратор `with_tenant_context`.

Контракт:
- Декорируем async-функцию таски, сигнатура `(tenant_id, session, *args, **kw)`.
- Декоратор:
  - открывает `tenant_session(tenant_id)`;
  - стартует транзакцию + ставит `SET LOCAL`;
  - вызывает тело таски, передавая активную сессию;
  - на исключении — откат, исключение пробрасывается;
  - на успехе — commit.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import pytest
import pytest_asyncio

from .conftest import TENANT_ALPHA, TENANT_BETA


pytestmark = pytest.mark.asyncio


def _import_helper():
    from app.core import celery_helpers
    return celery_helpers


# ---------------------------------------------------------------------------
# Контекст установлен внутри тела таски
# ---------------------------------------------------------------------------
async def test_decorator_sets_tenant_context(seed_customer):
    h = _import_helper()
    seed_customer(TENANT_ALPHA, "alpha")

    @h.with_tenant_context
    async def task(tenant_id, session: AsyncSession):
        result = await session.execute(text("SELECT app.current_tenant()"))
        return result.scalar()

    actual = await task(TENANT_ALPHA)
    assert str(actual) == str(TENANT_ALPHA)


async def test_decorator_isolates_per_call(seed_customer):
    h = _import_helper()
    seed_customer(TENANT_ALPHA, "alpha")
    seed_customer(TENANT_BETA, "beta-1")
    seed_customer(TENANT_BETA, "beta-2")

    @h.with_tenant_context
    async def count_customers(tenant_id, session: AsyncSession):
        r = await session.execute(text("SELECT count(*) FROM app.customers"))
        return r.scalar()

    n_alpha = await count_customers(TENANT_ALPHA)
    n_beta = await count_customers(TENANT_BETA)
    assert n_alpha == 1
    assert n_beta == 2


# ---------------------------------------------------------------------------
# Транзакционность
# ---------------------------------------------------------------------------
async def test_decorator_commits_on_success(migrator_conn):
    h = _import_helper()

    @h.with_tenant_context
    async def insert_one(tenant_id, session: AsyncSession):
        await session.execute(
            text("INSERT INTO app.customers (tenant_id, full_name, phone) "
                 "VALUES (app.current_tenant(), 'committed-by-task', '+1')")
        )

    await insert_one(TENANT_ALPHA)

    with migrator_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 1


async def test_decorator_rolls_back_on_exception(migrator_conn):
    h = _import_helper()

    class TaskBoom(RuntimeError):
        pass

    @h.with_tenant_context
    async def insert_then_raise(tenant_id, session: AsyncSession):
        await session.execute(
            text("INSERT INTO app.customers (tenant_id, full_name, phone) "
                 "VALUES (app.current_tenant(), 'should-roll-back', '+1')")
        )
        raise TaskBoom("intentional")

    with pytest.raises(TaskBoom):
        await insert_then_raise(TENANT_ALPHA)

    with migrator_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# Сигнатура: tenant_id первый аргумент
# ---------------------------------------------------------------------------
async def test_decorator_passes_through_extra_args():
    h = _import_helper()

    @h.with_tenant_context
    async def task(tenant_id, session: AsyncSession, x: int, *, y: int):
        return x + y

    result = await task(TENANT_ALPHA, 10, y=5)
    assert result == 15
