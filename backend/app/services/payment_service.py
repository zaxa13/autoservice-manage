from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.core.exceptions import NotFoundException, BadRequestException


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    return order


def _recalc_order_total_amount(order: Order) -> None:
    """Пересчитать total_amount заказа по работам и запчастям (в памяти)."""
    total_works = sum((w.total or Decimal("0")) for w in order.order_works)
    total_parts = sum((p.total or Decimal("0")) for p in order.order_parts)
    order.total_amount = total_works + total_parts


def recalc_order_paid_amount(db: Session, order: Order) -> None:
    """Пересчитать paid_amount по платежам в БД (учитывая только успешные)."""
    from sqlalchemy import func

    total_paid = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.order_id == order.id, Payment.status == PaymentStatus.SUCCEEDED)
        .scalar()
        or Decimal("0")
    )
    order.paid_amount = total_paid


def _update_order_status_after_payment_change(order: Order) -> None:
    """Обновить статус заказа после изменения оплат."""
    # Не трогаем завершенные/отмененные заказы
    if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
        return

    # Полностью оплачен
    if order.paid_amount >= order.total_amount - Decimal("0.01"):
        order.status = OrderStatus.PAID
    # Частично или не оплачен
    else:
        if order.paid_amount > Decimal("0"):
            # Можно пометить как READY_FOR_PAYMENT, если был NEW
            if order.status == OrderStatus.NEW:
                order.status = OrderStatus.READY_FOR_PAYMENT
        else:
            # Если оплат больше нет, а статус был PAID, откатываем
            if order.status == OrderStatus.PAID:
                order.status = OrderStatus.READY_FOR_PAYMENT


def get_payments_for_order(db: Session, order_id: int) -> List[Payment]:
    """Получить список платежей по заказу."""
    _get_order_or_404(db, order_id)
    return (
        db.query(Payment)
        .filter(Payment.order_id == order_id)
        .order_by(Payment.created_at.asc())
        .all()
    )


def create_manual_payment(
    db: Session,
    order_id: int,
    amount: Decimal,
    payment_method: PaymentMethod,
) -> Order:
    """Создать ручной платеж (наличные / карта и т.п.) и обновить заказ."""
    if amount <= Decimal("0"):
        raise BadRequestException("Сумма платежа должна быть больше нуля")

    order = _get_order_or_404(db, order_id)

    payment = Payment(
        order_id=order.id,
        amount=amount,
        payment_method=payment_method,
        status=PaymentStatus.SUCCEEDED,
    )
    db.add(payment)

    # Гарантируем, что платеж попадёт в БД перед пересчётом
    db.flush()

    # Пересчитываем суммы и статус заказа
    _recalc_order_total_amount(order)
    recalc_order_paid_amount(db, order)
    _update_order_status_after_payment_change(order)

    db.commit()
    db.refresh(order)
    return order


def cancel_payment(
    db: Session,
    order_id: int,
    payment_id: int,
    amount: Optional[Decimal],
) -> Order:
    """Отменить платеж полностью или частично и обновить заказ."""
    order = _get_order_or_404(db, order_id)

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.order_id == order_id)
        .first()
    )
    if not payment:
        raise NotFoundException("Платеж не найден")

    if payment.status != PaymentStatus.SUCCEEDED:
        raise BadRequestException("Можно отменить только успешный платеж")

    if amount is None:
        # Полная отмена платежа
        payment.status = PaymentStatus.CANCELLED
    else:
        amount = Decimal(str(amount))
        if amount <= Decimal("0"):
            raise BadRequestException("Сумма отмены должна быть больше нуля")
        if amount > payment.amount:
            raise BadRequestException("Сумма отмены больше суммы платежа")

        if amount == payment.amount:
            # Полная отмена
            payment.status = PaymentStatus.CANCELLED
        else:
            # Частичная отмена: уменьшаем исходный платеж и фиксируем возврат отдельной записью
            payment.amount = payment.amount - amount
            refund = Payment(
                order_id=order.id,
                amount=amount,
                payment_method=payment.payment_method,
                status=PaymentStatus.REFUNDED,
            )
            db.add(refund)

    # Пересчитываем сумму заказов и оплат и статус заказа
    _recalc_order_total_amount(order)
    recalc_order_paid_amount(db, order)
    _update_order_status_after_payment_change(order)

    db.commit()
    db.refresh(order)
    return order


def cancel_all_payments(db: Session, order_id: int) -> Order:
    """Отменить все успешные платежи по заказу и обновить заказ."""
    order = _get_order_or_404(db, order_id)

    for payment in order.payments:
        if payment.status == PaymentStatus.SUCCEEDED:
            payment.status = PaymentStatus.CANCELLED

    # Пересчитываем сумму заказов и оплат и статус заказа
    _recalc_order_total_amount(order)
    recalc_order_paid_amount(db, order)
    _update_order_status_after_payment_change(order)

    db.commit()
    db.refresh(order)
    return order

