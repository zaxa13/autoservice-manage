"""TDD: онбординг-сид tenant-defaults.

Контракт `app.services.tenant_onboarding.seed_tenant_defaults(session)`:
- работает внутри уже открытого `tenant_session` (current_tenant() != NULL);
- создаёт системные категории cashflow (income + expense);
- идемпотентен: повторный вызов не плодит дубликаты;
- не лезет в чужого тенанта (RLS);
- не имеет глобальных side-effects (никаких настроек/файлов).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from .conftest import TENANT_ALPHA, TENANT_BETA


pytestmark = pytest.mark.asyncio


def _import_seed():
    from app.services import tenant_onboarding
    return tenant_onboarding


@pytest_asyncio.fixture
async def alpha_session():
    """tenant_session под TENANT_ALPHA — переиспользуем рантайм-CM."""
    from app.database import tenant_session
    async with tenant_session(TENANT_ALPHA) as s:
        yield s


@pytest_asyncio.fixture
async def beta_session():
    from app.database import tenant_session
    async with tenant_session(TENANT_BETA) as s:
        yield s


# ---------------------------------------------------------------------------
# Базовое поведение
# ---------------------------------------------------------------------------
async def test_seed_creates_income_and_expense_categories(migrator_conn):
    """Проверяем КОНКРЕТНО что после сида в категориях есть income+expense."""
    onboarding = _import_seed()
    from app.database import tenant_session
    async with tenant_session(TENANT_ALPHA) as s:
        await onboarding.seed_tenant_defaults(s)

    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT transaction_type, count(*) FROM app.cash_transaction_categories "
            "WHERE tenant_id = %s AND is_system = true GROUP BY transaction_type",
            (str(TENANT_ALPHA),),
        )
        by_type = dict(cur.fetchall())

    assert by_type.get("income", 0) >= 1, "нет системных income-категорий"
    assert by_type.get("expense", 0) >= 1, "нет системных expense-категорий"


async def test_seed_is_idempotent(migrator_conn):
    onboarding = _import_seed()
    from app.database import tenant_session

    async with tenant_session(TENANT_ALPHA) as s:
        await onboarding.seed_tenant_defaults(s)
    async with tenant_session(TENANT_ALPHA) as s:
        await onboarding.seed_tenant_defaults(s)

    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM app.cash_transaction_categories "
            "WHERE tenant_id = %s AND is_system = true",
            (str(TENANT_ALPHA),),
        )
        first_count = cur.fetchone()[0]

    # И ещё раз
    from app.database import tenant_session as ts2
    async with ts2(TENANT_ALPHA) as s:
        await onboarding.seed_tenant_defaults(s)

    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM app.cash_transaction_categories "
            "WHERE tenant_id = %s AND is_system = true",
            (str(TENANT_ALPHA),),
        )
        third_count = cur.fetchone()[0]

    assert third_count == first_count


async def test_seed_only_affects_provided_tenant(migrator_conn):
    onboarding = _import_seed()
    from app.database import tenant_session

    async with tenant_session(TENANT_ALPHA) as s:
        await onboarding.seed_tenant_defaults(s)

    with migrator_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM app.cash_transaction_categories WHERE tenant_id=%s",
            (str(TENANT_BETA),),
        )
        assert cur.fetchone()[0] == 0, (
            "сид Alpha не должен создавать строки в Beta"
        )
