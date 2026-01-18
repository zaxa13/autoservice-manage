import httpx
import json
from sqlalchemy.orm import Session
from decimal import Decimal
from app.config import settings
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.order import Order
from app.models.integration import IntegrationLog, IntegrationType
from app.schemas.payment import PaymentYooKassaCreate


def create_yookassa_payment(db: Session, payment_create: PaymentYooKassaCreate) -> dict:
    """Создание платежа через ЮKassa"""
    # Проверка заказ-наряда
    order = db.query(Order).filter(Order.id == payment_create.order_id).first()
    if not order:
        raise ValueError("Заказ-наряд не найден")
    
    # Создание платежа в ЮKassa
    url = "https://api.yookassa.ru/v3/payments"
    headers = {
        "Authorization": f"Basic {settings.YOOKASSA_SECRET_KEY}",
        "Content-Type": "application/json",
        "Idempotence-Key": f"order_{order.id}_{order.number}"
    }
    
    payload = {
        "amount": {
            "value": str(payment_create.amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": payment_create.return_url or "https://autoservice.ru/payment/return"
        },
        "description": f"Оплата заказ-наряда {order.number}",
        "metadata": {
            "order_id": order.id,
            "order_number": order.number
        }
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            yookassa_data = response.json()
        
        # Сохранение платежа в БД
        payment = Payment(
            order_id=order.id,
            amount=payment_create.amount,
            payment_method=PaymentMethod.YOOKASSA,
            yookassa_payment_id=yookassa_data.get("id"),
            status=PaymentStatus.PENDING
        )
        db.add(payment)
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.YOOKASSA,
            status="success",
            request_data=json.dumps(payload),
            response_data=json.dumps(yookassa_data)
        )
        db.add(log)
        
        db.commit()
        
        return {
            "payment_id": payment.id,
            "yookassa_payment_id": yookassa_data.get("id"),
            "confirmation_url": yookassa_data.get("confirmation", {}).get("confirmation_url")
        }
    
    except httpx.HTTPError as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.YOOKASSA,
            status="error",
            request_data=json.dumps(payload),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        raise ValueError(f"Ошибка при создании платежа: {str(e)}")


def handle_yookassa_webhook(db: Session, webhook_data: dict) -> dict:
    """Обработка webhook от ЮKassa"""
    event = webhook_data.get("event")
    payment_data = webhook_data.get("object", {})
    yookassa_payment_id = payment_data.get("id")
    
    # Поиск платежа
    payment = db.query(Payment).filter(
        Payment.yookassa_payment_id == yookassa_payment_id
    ).first()
    
    if not payment:
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.YOOKASSA,
            status="error",
            request_data=json.dumps(webhook_data),
            response_data="Payment not found"
        )
        db.add(log)
        db.commit()
        return {"status": "error", "message": "Payment not found"}
    
    # Обновление статуса платежа
    status_mapping = {
        "pending": PaymentStatus.PENDING,
        "succeeded": PaymentStatus.SUCCEEDED,
        "canceled": PaymentStatus.CANCELLED
    }
    
    payment.status = status_mapping.get(payment_data.get("status"), PaymentStatus.PENDING)
    
    # Обновление суммы оплаты в заказ-наряде
    if payment.status == PaymentStatus.SUCCEEDED:
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order:
            order.paid_amount += payment.amount
    
    # Логирование
    log = IntegrationLog(
        integration_type=IntegrationType.YOOKASSA,
        status="success",
        request_data=json.dumps(webhook_data),
        response_data="Webhook processed"
    )
    db.add(log)
    
    db.commit()
    return {"status": "ok"}

