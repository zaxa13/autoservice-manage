"""Платежи через ЮКассу — create + webhook.

Webhook public (без auth): tenant_id извлекается из YooKassa-metadata.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_tenant_db
from app.integrations.yookassa import (
    create_yookassa_payment,
    handle_yookassa_webhook,
)
from app.schemas.payment import PaymentYooKassaCreate
from app.schemas.responses import (
    ErrorResponse,
    WebhookResponse,
    YooKassaPaymentResponse,
)

router = APIRouter()


@router.post(
    "/yookassa/create",
    response_model=YooKassaPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать платёж через ЮКассу",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        400: {"model": ErrorResponse, "description": "Ошибка создания / заказ не найден"},
    },
)
async def create_yookassa_payment_endpoint(
    body: PaymentYooKassaCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    try:
        return await create_yookassa_payment(db, tenant_id=claims.tenant_id, body=body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/yookassa/webhook",
    response_model=WebhookResponse,
    summary="Webhook ЮКасса",
    description=(
        "Public-эндпоинт без auth. tenant_id извлекается из metadata "
        "платежа, открывается tenant_session(tid) для обновления."
    ),
)
async def yookassa_webhook(request: Request) -> WebhookResponse:
    body = await request.json()
    result = await handle_yookassa_webhook(body)
    return result
