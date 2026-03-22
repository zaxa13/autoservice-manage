from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, OrderWork, OrderPart
from app.models.payment import Payment, PaymentStatus
from app.schemas.order import Order as OrderSchema, OrderCreate, OrderUpdate, OrderDetail
from app.schemas.payment import Payment as PaymentSchema, PaymentCreate, PaymentCancel
from app.schemas.responses import LabelValueItem, ErrorResponse
from app.services.order_service import create_order, update_order, complete_order
from app.services.payment_service import (
    get_payments_for_order,
    create_manual_payment,
    cancel_payment,
    cancel_all_payments,
)
from app.services.pdf_service import generate_order_pdf, generate_act_pdf
from app.core.permissions import require_manager_or_admin, require_admin
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Заказ-наряд не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}
_admin = {**_auth, 403: {"model": ErrorResponse, "description": "Только для администратора"}}


class OrderStatusInfo(BaseModel):
    value: str
    label: str


@router.get(
    "/statuses",
    response_model=List[OrderStatusInfo],
    status_code=status.HTTP_200_OK,
    summary="Статусы заказ-нарядов",
    description=(
        "Возвращает список доступных статусов для заказ-нарядов (без COMPLETED — "
        "он устанавливается только через операцию завершения)."
    ),
    responses=_auth,
)
def get_order_statuses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statuses = [
        OrderStatusInfo(value=OrderStatus.NEW.value, label="Новый"),
        OrderStatusInfo(value=OrderStatus.ESTIMATION.value, label="Проценка"),
        OrderStatusInfo(value=OrderStatus.IN_PROGRESS.value, label="В работе"),
        OrderStatusInfo(value=OrderStatus.READY_FOR_PAYMENT.value, label="Готов к оплате"),
        OrderStatusInfo(value=OrderStatus.PAID.value, label="Оплачен"),
        OrderStatusInfo(value=OrderStatus.CANCELLED.value, label="Отменен"),
    ]
    return statuses


@router.get(
    "/",
    response_model=List[OrderSchema],
    status_code=status.HTTP_200_OK,
    summary="Список заказ-нарядов",
    description=(
        "Возвращает заказ-наряды с пагинацией. Фильтрация по статусу. "
        "Механик видит только свои заказы. Суммы пересчитываются на лету."
    ),
    responses=_auth,
)
def get_orders(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    status_filter: Optional[OrderStatus] = Query(None, alias="status", description="Фильтр по статусу"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    from app.models.vehicle import Vehicle

    query = db.query(Order).options(
        joinedload(Order.vehicle).options(
            joinedload(Vehicle.customer),
            joinedload(Vehicle.brand),
            joinedload(Vehicle.vehicle_model),
        ),
        joinedload(Order.mechanic),
    )

    if current_user.role == UserRole.MECHANIC:
        query = query.filter(Order.mechanic_id == current_user.employee_id)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    for order in orders:
        total_works = sum((w.total or Decimal("0")) for w in order.order_works)
        total_parts = sum((p.total or Decimal("0")) for p in order.order_parts)
        order.total_amount = total_works + total_parts
        paid_amount = (
            db.query(func.sum(Payment.amount))
            .filter(
                Payment.order_id == order.id,
                Payment.status == PaymentStatus.SUCCEEDED,
            )
            .scalar()
            or Decimal("0")
        )
        order.paid_amount = paid_amount

    return orders


@router.get(
    "/{order_id}",
    response_model=OrderDetail,
    status_code=status.HTTP_200_OK,
    summary="Получить заказ-наряд по ID",
    description=(
        "Детальная информация по заказ-наряду: работы, запчасти, сотрудники, оплаты. "
        "Механик видит только свои заказы (403 при чужом). "
        "Суммы пересчитываются на лету."
    ),
    responses={**_auth, 403: {"model": ErrorResponse, "description": "Нет доступа к этому заказу"}, **_404},
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    from app.models.vehicle import Vehicle

    order = db.query(Order).options(
        joinedload(Order.vehicle).options(
            joinedload(Vehicle.customer),
            joinedload(Vehicle.brand),
            joinedload(Vehicle.vehicle_model),
        ),
        joinedload(Order.employee),
        joinedload(Order.mechanic),
        joinedload(Order.order_works).joinedload(OrderWork.work),
        joinedload(Order.order_parts).joinedload(OrderPart.part),
    ).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")

    if current_user.role == UserRole.MECHANIC:
        if order.mechanic_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому заказ-наряду",
            )

    total_works = sum((w.total or Decimal("0")) for w in order.order_works)
    total_parts = sum((p.total or Decimal("0")) for p in order.order_parts)
    order.total_amount = total_works + total_parts

    paid_amount = (
        db.query(func.sum(Payment.amount))
        .filter(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.SUCCEEDED,
        )
        .scalar()
        or Decimal("0")
    )
    order.paid_amount = paid_amount

    return order


@router.post(
    "/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ-наряд",
    description=(
        "Создание нового заказ-наряда. Номер генерируется автоматически. "
        "Если у администратора нет привязанного сотрудника — используется системный. "
        "Доступно менеджеру и администратору."
    ),
    responses={**_write, 400: {"model": ErrorResponse, "description": "Нет активных сотрудников / не привязан сотрудник"}},
)
def create_new_order(
    order_create: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    employee_id = current_user.employee_id

    if not employee_id and current_user.role == UserRole.ADMIN:
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True,
        ).first()

        if system_admin:
            employee_id = system_admin.id
        else:
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника.",
                )
    elif not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник",
        )

    order = create_order(db, order_create, employee_id)
    return order


@router.put(
    "/{order_id}",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить заказ-наряд",
    description=(
        "Обновление заказ-наряда: статус, механик, работы, запчасти, рекомендации, комментарии. "
        "При передаче списков работ/запчастей они полностью заменяются."
    ),
    responses={**_write, **_404},
)
def update_existing_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    order = update_order(db, order_id, order_update)
    return order


@router.post(
    "/{order_id}/complete",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    summary="Завершить заказ-наряд",
    description=(
        "Установка статуса COMPLETED и фиксация даты завершения. "
        "Суммы пересчитываются перед возвратом."
    ),
    responses={**_auth, 400: {"model": ErrorResponse, "description": "Нет привязанного сотрудника"}, **_404},
)
def complete_existing_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee_id = current_user.employee_id

    if not employee_id and current_user.role == UserRole.ADMIN:
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True,
        ).first()

        if system_admin:
            employee_id = system_admin.id
        else:
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника.",
                )
    elif not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник",
        )

    from sqlalchemy import func

    order = complete_order(db, order_id, employee_id)

    total_works = sum((w.total or Decimal("0")) for w in order.order_works)
    total_parts = sum((p.total or Decimal("0")) for p in order.order_parts)
    order.total_amount = total_works + total_parts

    paid_amount = (
        db.query(func.sum(Payment.amount))
        .filter(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.SUCCEEDED,
        )
        .scalar()
        or Decimal("0")
    )
    order.paid_amount = paid_amount

    return order


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заказ-наряд",
    description=(
        "Полное удаление заказ-наряда вместе с платежами, работами и запчастями. "
        "Связанные записи (appointments) отвязываются. Только администратор."
    ),
    responses={**_admin, **_404},
)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только администратор может удалять заказы")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")

    db.query(Payment).filter(Payment.order_id == order_id).delete()
    from app.models.appointment import Appointment
    db.query(Appointment).filter(Appointment.order_id == order_id).update({Appointment.order_id: None})
    db.delete(order)
    db.commit()
    return None


@router.post(
    "/{order_id}/cancel",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    summary="Отменить заказ-наряд",
    description="Установка статуса CANCELLED. Доступно менеджеру и администратору.",
    responses={**_write, **_404},
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")

    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order


@router.get(
    "/{order_id}/payments",
    response_model=List[PaymentSchema],
    status_code=status.HTTP_200_OK,
    summary="Платежи по заказу",
    description="Возвращает список всех платежей по заказ-наряду.",
    responses={**_write, **_404},
)
def list_order_payments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    payments = get_payments_for_order(db, order_id)
    return payments


@router.post(
    "/{order_id}/payments",
    response_model=OrderDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Создать оплату",
    description=(
        "Создание ручной оплаты по заказ-наряду (наличные, карта и т.п.). "
        "`order_id` в теле запроса должен совпадать с параметром пути."
    ),
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Несовпадение order_id"},
        **_404,
    },
)
def create_order_payment(
    order_id: int,
    payment_create: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    if payment_create.order_id != order_id:
        raise BadRequestException("order_id в запросе и в теле не совпадают")

    order = create_manual_payment(
        db,
        order_id=order_id,
        amount=payment_create.amount,
        payment_method=payment_create.payment_method,
    )
    return order


@router.post(
    "/{order_id}/payments/{payment_id}/cancel",
    response_model=OrderDetail,
    status_code=status.HTTP_200_OK,
    summary="Отменить платёж",
    description="Полная или частичная отмена платежа. При `amount: null` — отмена всей суммы.",
    responses={**_write, **_404},
)
def cancel_order_payment(
    order_id: int,
    payment_id: int,
    cancel_data: PaymentCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    order = cancel_payment(
        db,
        order_id=order_id,
        payment_id=payment_id,
        amount=cancel_data.amount,
    )
    return order


@router.post(
    "/{order_id}/payments/cancel-all",
    response_model=OrderDetail,
    status_code=status.HTTP_200_OK,
    summary="Отменить все платежи",
    description="Отмена всех платежей по заказ-наряду. Только администратор.",
    responses={**_admin, **_404},
)
def cancel_all_order_payments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order = cancel_all_payments(db, order_id)
    return order


@router.put(
    "/{order_id}/payments/{payment_id}",
    response_model=PaymentSchema,
    status_code=status.HTTP_200_OK,
    summary="Редактировать платёж",
    description="Изменение суммы и способа оплаты существующего платежа. Только администратор.",
    responses={
        **_admin,
        404: {"model": ErrorResponse, "description": "Заказ или платёж не найден"},
    },
)
def update_order_payment(
    order_id: int,
    payment_id: int,
    payment_update: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")

    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.order_id == order_id,
    ).first()
    if not payment:
        raise NotFoundException("Платёж не найден")

    old_method = payment.payment_method
    payment.amount = payment_update.amount
    payment.payment_method = payment_update.payment_method

    db.flush()

    # Синхронизируем кассовую транзакцию
    from app.services.cashflow_service import adjust_order_cashflow_transaction
    adjust_order_cashflow_transaction(
        db,
        order_id=order_id,
        new_amount=payment_update.amount,
        new_payment_method=payment_update.payment_method.value,
        payment_id=payment_id,
    )

    # Пересчитываем paid_amount и статус заказа
    from app.services.payment_service import recalc_order_paid_amount, _recalc_order_total_amount, _update_order_status_after_payment_change
    _recalc_order_total_amount(order)
    recalc_order_paid_amount(db, order)
    _update_order_status_after_payment_change(order)

    db.commit()
    db.refresh(payment)

    return payment


@router.get(
    "/{order_id}/print",
    status_code=status.HTTP_200_OK,
    summary="PDF заказ-наряда",
    description="Генерирует и возвращает PDF-файл заказ-наряда.",
    responses={**_auth, **_404},
)
def print_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_bytes = generate_order_pdf(db, order_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=order-{order_id}.pdf"},
    )


@router.get(
    "/{order_id}/print-act",
    status_code=status.HTTP_200_OK,
    summary="PDF акта выполненных работ",
    description="Генерирует и возвращает PDF-файл акта выполненных работ.",
    responses={**_auth, **_404},
)
def print_act(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_bytes = generate_act_pdf(db, order_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=act-{order_id}.pdf"},
    )
