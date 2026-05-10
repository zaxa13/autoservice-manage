"""Общий helper для интеграций: создаёт `httpx.AsyncClient` и пишет лог."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationLog, IntegrationType


# Глобальный transport. В тестах подменяется через monkeypatch:
#   app.integrations._helpers._TRANSPORT = httpx.MockTransport(handler)
_TRANSPORT: httpx.AsyncBaseTransport | None = None


def make_async_client(timeout: float = 10.0) -> httpx.AsyncClient:
    """Создаёт async-клиент. Если установлен `_TRANSPORT` (тестовый) —
    использует его, иначе обычный сетевой."""
    if _TRANSPORT is not None:
        return httpx.AsyncClient(transport=_TRANSPORT, timeout=timeout)
    return httpx.AsyncClient(timeout=timeout)


async def log_integration(
    db: AsyncSession,
    *,
    tenant_id,
    integration_type: IntegrationType,
    status: str,
    request_data: dict | None,
    response_data,
) -> None:
    """Записывает один IntegrationLog в текущей транзакции."""
    db.add(IntegrationLog(
        tenant_id=tenant_id,
        integration_type=integration_type.value,
        status=status,
        request_data=json.dumps(request_data) if request_data is not None else None,
        response_data=(
            json.dumps(response_data)
            if isinstance(response_data, (dict, list))
            else str(response_data)
        ),
    ))
