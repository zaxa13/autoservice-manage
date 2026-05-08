"""Celery-декоратор для выполнения тасок в tenant-контексте.

Использование:

    from app.core.celery_helpers import with_tenant_context

    @celery_app.task(name="orders.recalc_totals")
    @with_tenant_context
    async def recalc_totals(tenant_id, session, order_id: int) -> None:
        ...

Контракт:
- Декорируемая функция принимает `(tenant_id, session, *args, **kwargs)`.
- Декоратор открывает `tenant_session(tenant_id)`, передаёт активную
  AsyncSession как второй аргумент.
- Транзакция коммитится по выходу, откатывается на исключении.
"""
from __future__ import annotations

import uuid
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import tenant_session

P = ParamSpec("P")
R = TypeVar("R")


def with_tenant_context(
    func: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    """Оборачивает async-таску в `tenant_session`.

    Принимает `tenant_id` первым позиционным аргументом, остальное
    передаётся в тело таски как есть. Сессия — второй аргумент.
    """

    @wraps(func)
    async def wrapper(tenant_id: uuid.UUID | str, *args: Any, **kwargs: Any) -> R:
        if isinstance(tenant_id, str):
            tenant_id = uuid.UUID(tenant_id)
        async with tenant_session(tenant_id) as session:
            return await func(tenant_id, session, *args, **kwargs)

    return wrapper
