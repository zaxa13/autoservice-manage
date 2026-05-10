"""Поиск/заказ запчастей у внешних поставщиков — async."""
from __future__ import annotations

import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations._helpers import log_integration, make_async_client
from app.models.integration import IntegrationType


async def search_parts(
    db: AsyncSession, *, tenant_id: uuid.UUID, query: str
) -> dict:
    url = f"{settings.PARTS_SUPPLIER_API_URL}/search"
    headers = {
        "Authorization": f"Bearer {settings.PARTS_SUPPLIER_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {"query": query}
    try:
        async with make_async_client() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.PARTS_SUPPLIER,
            status="success", request_data=params, response_data=result,
        )
        return result
    except httpx.HTTPError as e:
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.PARTS_SUPPLIER,
            status="error", request_data=params, response_data=str(e),
        )
        return {"error": str(e), "results": []}


async def create_supplier_order(
    db: AsyncSession, *, tenant_id: uuid.UUID, order_data: dict
) -> dict:
    url = f"{settings.PARTS_SUPPLIER_API_URL}/orders"
    headers = {
        "Authorization": f"Bearer {settings.PARTS_SUPPLIER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with make_async_client() as client:
            response = await client.post(url, headers=headers, json=order_data)
            response.raise_for_status()
            result = response.json()
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.PARTS_SUPPLIER,
            status="success", request_data=order_data, response_data=result,
        )
        return result
    except httpx.HTTPError as e:
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.PARTS_SUPPLIER,
            status="error", request_data=order_data, response_data=str(e),
        )
        return {"error": str(e)}
