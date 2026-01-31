from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.order import Order as OrderSchema, OrderCreate, OrderUpdate, OrderDetail
from app.schemas.payment import Payment as PaymentSchema, PaymentCreate, PaymentCancel
from app.services.order_service import create_order, update_order, complete_order
from app.services.payment_service import (
    get_payments_for_order,
    create_manual_payment,
    cancel_payment,
    cancel_all_payments,
)
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter()


class OrderStatusInfo(BaseModel):
    value: str
    label: str


@router.get("/statuses", response_model=List[OrderStatusInfo])
def get_order_statuses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка доступных статусов заказ-нарядов"""
    # Исключаем COMPLETED из списка - он устанавливается только через кнопку "завершить"
    statuses = [
        OrderStatusInfo(value=OrderStatus.NEW.value, label="Новый"),
        OrderStatusInfo(value=OrderStatus.ESTIMATION.value, label="Проценка"),
        OrderStatusInfo(value=OrderStatus.IN_PROGRESS.value, label="В работе"),
        OrderStatusInfo(value=OrderStatus.READY_FOR_PAYMENT.value, label="Готов к оплате"),
        OrderStatusInfo(value=OrderStatus.PAID.value, label="Оплачен"),
        OrderStatusInfo(value=OrderStatus.CANCELLED.value, label="Отменен"),
    ]
    return statuses


@router.get("/", response_model=List[OrderSchema])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка заказ-нарядов"""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    from app.models.vehicle import Vehicle
    
    query = db.query(Order).options(
        joinedload(Order.vehicle).joinedload(Vehicle.customer),
        joinedload(Order.mechanic)
    )
    
    # Механик видит только свои заказ-наряды
    if current_user.role == UserRole.MECHANIC:
        query = query.filter(Order.mechanic_id == current_user.employee_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    # Пересчитываем суммы для каждого заказа, чтобы список возвращал актуальные данные
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


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение заказ-наряда по ID"""
    from sqlalchemy import func

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    # Проверка прав доступа для механика
    if current_user.role == UserRole.MECHANIC:
        if order.mechanic_id != current_user.employee_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому заказ-наряду"
            )

    # Пересчет общей суммы на основе работ и запчастей,
    # чтобы исключить рассинхрон между total_amount и позициями
    total_works = sum((w.total or Decimal("0")) for w in order.order_works)
    total_parts = sum((p.total or Decimal("0")) for p in order.order_parts)
    order.total_amount = total_works + total_parts

    # Пересчёт оплаченной суммы на основе платежей
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


@router.post("/", response_model=OrderSchema)
def create_new_order(
    order_create: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание нового заказ-наряда"""
    # Для администраторов employee_id может быть не задан
    # В этом случае пытаемся найти или создать системного сотрудника-администратора
    employee_id = current_user.employee_id
    
    if not employee_id and current_user.role == UserRole.ADMIN:
        # Ищем системного сотрудника-администратора
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True
        ).first()
        
        if system_admin:
            employee_id = system_admin.id
        else:
            # Если нет ни одного администратора-сотрудника, берем первого активного сотрудника
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника."
                )
    elif not employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    
    order = create_order(db, order_create, employee_id)
    return order


@router.put("/{order_id}", response_model=OrderSchema)
def update_existing_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление заказ-наряда"""
    order = update_order(db, order_id, order_update)
    return order


@router.post("/{order_id}/complete", response_model=OrderSchema)
def complete_existing_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Завершение заказ-наряда"""
    # Для администраторов employee_id может быть не задан
    # В этом случае пытаемся найти системного сотрудника-администратора
    employee_id = current_user.employee_id
    
    if not employee_id and current_user.role == UserRole.ADMIN:
        # Ищем системного сотрудника-администратора
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True
        ).first()
        
        if system_admin:
            employee_id = system_admin.id
        else:
            # Если нет ни одного администратора-сотрудника, берем первого активного сотрудника
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника."
                )
    elif not employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    
    from sqlalchemy import func

    order = complete_order(db, order_id, employee_id)

    # Пересчёт total_amount и paid_amount перед возвратом, чтобы не зависеть от
    # возможного устаревшего значения в БД
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


@router.post("/{order_id}/cancel", response_model=OrderSchema)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Отмена заказ-наряда"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}/payments", response_model=List[PaymentSchema])
def list_order_payments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Получение списка оплат по заказ-наряду."""
    payments = get_payments_for_order(db, order_id)
    return payments


@router.post("/{order_id}/payments", response_model=OrderDetail)
def create_order_payment(
    order_id: int,
    payment_create: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Создание оплаты по заказ-наряду (наличные/карта и т.п.)."""
    if payment_create.order_id != order_id:
        raise BadRequestException("order_id в запросе и в теле не совпадают")

    order = create_manual_payment(
        db,
        order_id=order_id,
        amount=payment_create.amount,
        payment_method=payment_create.payment_method,
    )
    return order


@router.post("/{order_id}/payments/{payment_id}/cancel", response_model=OrderDetail)
def cancel_order_payment(
    order_id: int,
    payment_id: int,
    cancel_data: PaymentCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Отмена оплаты по заказ-наряду (полная или частичная)."""
    order = cancel_payment(
        db,
        order_id=order_id,
        payment_id=payment_id,
        amount=cancel_data.amount,
    )
    return order


@router.post("/{order_id}/payments/cancel-all", response_model=OrderDetail)
def cancel_all_order_payments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Отмена всех оплат по заказ-наряду."""
    order = cancel_all_payments(db, order_id)
    return order

