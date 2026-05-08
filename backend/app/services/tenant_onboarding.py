"""Онбординг тенанта: посев системных справочников при первой регистрации.

Вызывается из platform-api после `INSERT INTO platform.tenants` в той же
транзакции (или отдельной, под `tenant_session(new_tenant_id)`).

Все операции — внутри уже открытой `tenant_session`, читают `tenant_id`
из GUC `app.tenant_id` через `app.current_tenant()`.

Идемпотентность: повторный вызов на уже посеянного тенанта — no-op.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cashflow import CashflowTransactionType, TransactionCategory


# Системные категории cashflow. Имена — на русском, чтобы видеть в UI без
# i18n-слоя. При реальной i18n-локализации UI будет резолвить по `is_system`-флагу.
_DEFAULT_CASHFLOW_CATEGORIES: list[tuple[str, str]] = [
    ("Оплата заказа",         CashflowTransactionType.INCOME.value),
    ("Возврат клиенту",       CashflowTransactionType.EXPENSE.value),
    ("Зарплата",              CashflowTransactionType.EXPENSE.value),
    ("Закупка запчастей",     CashflowTransactionType.EXPENSE.value),
    ("Аренда",                CashflowTransactionType.EXPENSE.value),
    ("Налоги",                CashflowTransactionType.EXPENSE.value),
    ("Прочий доход",          CashflowTransactionType.INCOME.value),
    ("Прочий расход",         CashflowTransactionType.EXPENSE.value),
]


class _TenantContextNotSet(RuntimeError):
    pass


async def _current_tenant(session: AsyncSession):
    result = await session.execute(text("SELECT app.current_tenant()"))
    tid = result.scalar()
    if tid is None:
        raise _TenantContextNotSet(
            "seed_tenant_defaults must run inside tenant_session(...)"
        )
    return tid


async def seed_tenant_defaults(session: AsyncSession) -> None:
    """Идемпотентный сид системных справочников для тенанта."""
    tenant_id = await _current_tenant(session)

    # Идемпотентность: если хоть одна системная категория уже есть — пропускаем.
    existing = await session.execute(
        select(func.count())
        .select_from(TransactionCategory)
        .where(TransactionCategory.is_system.is_(True))
    )
    if (existing.scalar() or 0) > 0:
        return

    for name, ttype in _DEFAULT_CASHFLOW_CATEGORIES:
        session.add(
            TransactionCategory(
                tenant_id=tenant_id,
                name=name,
                transaction_type=ttype,
                is_system=True,
                is_active=True,
            )
        )
    await session.flush()
