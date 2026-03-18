from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentYooKassaCreate
from app.schemas.responses import YooKassaPaymentResponse, WebhookResponse, ErrorResponse
from app.core.permissions import require_manager_or_admin
from app.integrations.yookassa import create_yookassa_payment, handle_yookassa_webhook

router = APIRouter()

_write = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Недостаточно прав"},
}


@router.post(
    "/yookassa/create",
    response_model=YooKassaPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать платёж через YooKassa",
    description=(
        "Создание платежа через платёжную систему YooKassa. "
        "Возвращает URL для перенаправления клиента на страницу оплаты. "
        "Возвращает 400 при ошибке на стороне YooKassa или если заказ не найден."
    ),
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Ошибка создания платежа / заказ не найден"},
    },
)
def create_yookassa_payment_endpoint(
    payment_create: PaymentYooKassaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    try:
        payment_data = create_yookassa_payment(db, payment_create)
        return payment_data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/yookassa/webhook",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Webhook YooKassa",
    description=(
        "Эндпоинт для приёма уведомлений от YooKassa об изменении статуса платежа. "
        "При статусе `succeeded` автоматически обновляется оплаченная сумма заказа. "
        "Публичный эндпоинт — без JWT авторизации."
    ),
)
async def yookassa_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.json()
    result = handle_yookassa_webhook(db, body)
    return result
