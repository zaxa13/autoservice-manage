"""ГИБДД integration — async."""
from __future__ import annotations

import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations._helpers import log_integration, make_async_client
from app.models.integration import IntegrationType


async def check_vehicle_gibdd(
    db: AsyncSession, *, tenant_id: uuid.UUID, vin: str
) -> dict:
    """Проверка ТС в ГИБДД. Возвращает либо raw результат API,
    либо `{"error": "..."}` при ошибке."""
    url = f"{settings.GIBDD_API_URL}/vehicle/check"
    headers = {
        "Authorization": f"Bearer {settings.GIBDD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"vin": vin}

    try:
        async with make_async_client() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.GIBDD,
            status="success", request_data=payload, response_data=result,
        )
        return result
    except httpx.HTTPError as e:
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.GIBDD,
            status="error", request_data=payload, response_data=str(e),
        )
        return {"error": str(e)}
