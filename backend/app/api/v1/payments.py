from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.payment import Payment as PaymentSchema, PaymentYooKassaCreate
from app.core.permissions import require_manager_or_admin
from app.integrations.yookassa import create_yookassa_payment, handle_yookassa_webhook

router = APIRouter()


@router.post("/yookassa/create", response_model=dict)
def create_yookassa_payment_endpoint(
    payment_create: PaymentYooKassaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание платежа через ЮKassa"""
    payment_data = create_yookassa_payment(db, payment_create)
    return payment_data


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Webhook для обработки уведомлений от ЮKassa"""
    body = await request.json()
    result = handle_yookassa_webhook(db, body)
    return result

