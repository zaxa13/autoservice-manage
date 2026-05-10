"""ЮКасса — async create + webhook handler.

create_yookassa_payment работает в tenant-контексте: создаёт Payment
со статусом pending, плюс лог. tenant_id кладём в metadata YooKassa,
чтобы webhook мог его прочитать без auth.

handle_yookassa_webhook — public endpoint без auth. Из metadata
извлекает tenant_id, открывает `tenant_session(tid)` и обновляет
платёж/заказ.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import tenant_session
from app.integrations._helpers import log_integration, make_async_client
from app.models.integration import IntegrationType
from app.models.order import Order
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.schemas.payment import PaymentYooKassaCreate


async def create_yookassa_payment(
    db: AsyncSession, *, tenant_id: uuid.UUID, body: PaymentYooKassaCreate
) -> dict:
    """Создаёт ЮКасса-платёж + Payment(pending) для текущего тенанта."""
    order = await db.get(Order, (tenant_id, body.order_id))
    if order is None:
        raise ValueError("Заказ-наряд не найден")

    url = "https://api.yookassa.ru/v3/payments"
    headers = {
        "Authorization": f"Basic {settings.YOOKASSA_SECRET_KEY}",
        "Content-Type": "application/json",
        "Idempotence-Key": f"order_{tenant_id}_{order.id}_{order.number}",
    }
    payload = {
        "amount": {"value": str(body.amount), "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": body.return_url or "https://autoservice.ru/payment/return",
        },
        "description": f"Оплата заказ-наряда {order.number}",
        "metadata": {
            "order_id": order.id,
            "order_number": order.number,
            "tenant_id": str(tenant_id),
        },
    }

    try:
        async with make_async_client() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            yk_data = response.json()
    except httpx.HTTPError as e:
        await log_integration(
            db, tenant_id=tenant_id, integration_type=IntegrationType.YOOKASSA,
            status="error", request_data=payload, response_data=str(e),
        )
        raise ValueError(f"Ошибка при создании платежа: {e}")

    payment = Payment(
        tenant_id=tenant_id,
        order_id=order.id,
        amount=body.amount,
        payment_method=PaymentMethod.YOOKASSA.value,
        yookassa_payment_id=yk_data.get("id"),
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    await log_integration(
        db, tenant_id=tenant_id, integration_type=IntegrationType.YOOKASSA,
        status="success", request_data=payload, response_data=yk_data,
    )
    await db.flush()
    await db.refresh(payment)

    return {
        "payment_id": payment.id,
        "yookassa_payment_id": yk_data.get("id"),
        "confirmation_url": (
            yk_data.get("confirmation", {}).get("confirmation_url")
            if isinstance(yk_data.get("confirmation"), dict) else None
        ),
    }


_STATUS_MAP = {
    "pending": PaymentStatus.PENDING.value,
    "succeeded": PaymentStatus.SUCCEEDED.value,
    "canceled": PaymentStatus.CANCELLED.value,
}


async def handle_yookassa_webhook(webhook_data: dict) -> dict:
    """Public webhook: обрабатывает уведомление от ЮКасса.

    tenant_id извлекается из metadata. Если нет — return error без записи
    (не знаем под каким tenant писать лог)."""
    obj = webhook_data.get("object", {}) or {}
    yk_id = obj.get("id")
    metadata = obj.get("metadata") or {}
    tenant_id_str = metadata.get("tenant_id")
    if not tenant_id_str or not yk_id:
        return {"status": "error", "message": "Missing tenant_id or payment id in webhook"}
    try:
        tid = uuid.UUID(tenant_id_str)
    except ValueError:
        return {"status": "error", "message": "Invalid tenant_id in metadata"}

    new_yk_status = obj.get("status")
    target_status = _STATUS_MAP.get(new_yk_status)

    async with tenant_session(tid) as session:
        payment = (await session.execute(
            select(Payment).where(Payment.yookassa_payment_id == yk_id)
        )).scalar_one_or_none()
        if payment is None:
            await log_integration(
                session, tenant_id=tid, integration_type=IntegrationType.YOOKASSA,
                status="error", request_data=webhook_data, response_data="payment not found",
            )
            return {"status": "error", "message": "Payment not found"}

        if target_status is not None:
            payment.status = target_status

        if target_status == PaymentStatus.SUCCEEDED.value:
            order = await session.get(Order, (tid, payment.order_id))
            if order is not None:
                order.paid_amount = (
                    Decimal(str(order.paid_amount or 0))
                    + Decimal(str(payment.amount))
                )

        await log_integration(
            session, tenant_id=tid, integration_type=IntegrationType.YOOKASSA,
            status="success", request_data=webhook_data, response_data="processed",
        )

    return {"status": "ok"}
