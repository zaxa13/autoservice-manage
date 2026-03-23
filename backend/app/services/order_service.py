from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from app.models.order import Order, OrderStatus, OrderWork, OrderPart
from app.models.warehouse import WarehouseItem, WarehouseTransaction, TransactionType
from app.schemas.order import OrderCreate, OrderUpdate
from app.core.exceptions import NotFoundException, BadRequestException


def generate_order_number(db: Session) -> str:
    """Генерация уникального номера заказ-наряда"""
    today = datetime.now().strftime("%Y%m%d")
    last_order = db.query(Order).filter(Order.number.like(f"ORD-{today}-%")).order_by(Order.number.desc()).first()
    
    if last_order:
        last_num = int(last_order.number.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"ORD-{today}-{new_num:04d}"


def create_order(db: Session, order_create: OrderCreate, employee_id: int) -> Order:
    """Создание заказ-наряда"""
    from app.models.vehicle import Vehicle

    order_number = generate_order_number(db)
    
    # Snapshot пробега авто на момент создания заказа
    mileage = order_create.mileage_at_service
    if mileage is None:
        vehicle = db.query(Vehicle).filter(Vehicle.id == order_create.vehicle_id).first()
        if vehicle:
            mileage = vehicle.mileage
    
    # Расчет общей суммы
    total_amount = Decimal(0)
    
    # Создание заказ-наряда
    order = Order(
        number=order_number,
        vehicle_id=order_create.vehicle_id,
        employee_id=employee_id,
        mechanic_id=order_create.mechanic_id,
        status=OrderStatus.NEW,
        total_amount=0,
        paid_amount=0,
        mileage_at_service=mileage,
        recommendations=order_create.recommendations,
        comments=order_create.comments
    )
    db.add(order)
    db.flush()
    
    # Добавление работ
    for work_data in order_create.order_works:
        # Расчет с учетом скидки
        discount = work_data.discount or Decimal(0)
        price_with_discount = work_data.price * (1 - discount / 100)
        work_total = price_with_discount * work_data.quantity
        total_amount += work_total
        order_work = OrderWork(
            order_id=order.id,
            work_id=work_data.work_id,
            work_name=work_data.work_name,
            mechanic_id=work_data.mechanic_id,
            quantity=work_data.quantity,
            price=work_data.price,
            discount=discount,
            total=work_total
        )
        db.add(order_work)
    
    # Добавление запчастей
    for part_data in order_create.order_parts:
        # Расчет с учетом скидки
        discount = part_data.discount or Decimal(0)
        price_with_discount = part_data.price * (1 - discount / 100)
        part_total = price_with_discount * part_data.quantity
        total_amount += part_total
        order_part = OrderPart(
            order_id=order.id,
            part_id=part_data.part_id,
            part_name=part_data.part_name,
            article=part_data.article,
            quantity=part_data.quantity,
            price=part_data.price,
            discount=discount,
            total=part_total
        )
        db.add(order_part)
    
    order.total_amount = total_amount
    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, order_id: int, order_update: OrderUpdate) -> Order:
    """Обновление заказ-наряда"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    if order_update.employee_id is not None:
        order.employee_id = order_update.employee_id

    if order_update.mechanic_id is not None:
        order.mechanic_id = order_update.mechanic_id
    
    if order_update.recommendations is not None:
        order.recommendations = order_update.recommendations
    
    if order_update.comments is not None:
        order.comments = order_update.comments
    
    # Обработка оплаты: paid_amount - это сумма нового платежа, который добавляется к текущему
    if order_update.paid_amount is not None:
        payment_amount = Decimal(str(order_update.paid_amount))
        if payment_amount < 0:
            raise BadRequestException("Сумма платежа не может быть отрицательной")
        
        # Добавляем новый платеж к уже оплаченной сумме
        order.paid_amount = (order.paid_amount or Decimal(0)) + payment_amount
        
        # Если после добавления оплаты сумма равна или превышает общую сумму, устанавливаем статус PAID
        if order.paid_amount >= order.total_amount - Decimal('0.01'):  # Допускаем небольшую погрешность
            if order.status != OrderStatus.COMPLETED and order.status != OrderStatus.CANCELLED:
                order.status = OrderStatus.PAID
                if not order.completed_at:
                    order.completed_at = datetime.utcnow()
    
    if order_update.status is not None:
        order.status = order_update.status
        if order_update.status == OrderStatus.READY_FOR_PAYMENT or order_update.status == OrderStatus.PAID:
            if not order.completed_at:
                order.completed_at = datetime.utcnow()
    
    # Обновление работ и запчастей
    if order_update.order_works is not None:
        # Удаляем старые работы
        db.query(OrderWork).filter(OrderWork.order_id == order_id).delete()
        # Добавляем новые
        total_amount = Decimal(0)
        for work_data in order_update.order_works:
            # Расчет с учетом скидки
            discount = work_data.discount or Decimal(0)
            price_with_discount = work_data.price * (1 - discount / 100)
            work_total = price_with_discount * work_data.quantity
            total_amount += work_total
            order_work = OrderWork(
                order_id=order.id,
                work_id=work_data.work_id,
                work_name=work_data.work_name,
                mechanic_id=work_data.mechanic_id,
                quantity=work_data.quantity,
                price=work_data.price,
                discount=discount,
                total=work_total
            )
            db.add(order_work)
        
        # Пересчитываем общую сумму по текущим данным (работы + запчасти),
        # чтобы избежать рассинхрона, если что-то изменилось отдельно
        parts_total = db.query(func.sum(OrderPart.total)).filter(OrderPart.order_id == order_id).scalar() or Decimal(0)
        order.total_amount = total_amount + parts_total
    
    if order_update.order_parts is not None:
        # Удаляем старые запчасти
        db.query(OrderPart).filter(OrderPart.order_id == order_id).delete()
        # Добавляем новые
        total_amount = Decimal(0)
        for part_data in order_update.order_parts:
            # Расчет с учетом скидки
            discount = part_data.discount or Decimal(0)
            price_with_discount = part_data.price * (1 - discount / 100)
            part_total = price_with_discount * part_data.quantity
            total_amount += part_total
            order_part = OrderPart(
                order_id=order.id,
                part_id=part_data.part_id,
                part_name=part_data.part_name,
                article=part_data.article,
                quantity=part_data.quantity,
                price=part_data.price,
                discount=discount,
                total=part_total
            )
            db.add(order_part)
        
        # Пересчитываем общую сумму по текущим данным (работы + запчасти),
        # чтобы избежать рассинхрона, если что-то изменилось отдельно
        works_total = db.query(func.sum(OrderWork.total)).filter(OrderWork.order_id == order_id).scalar() or Decimal(0)
        order.total_amount = total_amount + works_total

    # Финальный пересчет общей суммы из БД на случай сложных сценариев,
    # когда менялись и работы, и запчасти, и могли быть нестандартные сочетания полей
    works_total_final = db.query(func.sum(OrderWork.total)).filter(OrderWork.order_id == order_id).scalar() or Decimal(0)
    parts_total_final = db.query(func.sum(OrderPart.total)).filter(OrderPart.order_id == order_id).scalar() or Decimal(0)
    order.total_amount = works_total_final + parts_total_final

    db.commit()
    db.refresh(order)
    return order


def complete_order(db: Session, order_id: int, employee_id: int) -> Order:
    """Закрытие заказ-наряда. Разрешено только при статусе «Оплачен». Списываем запчасти со склада только при оплате."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    if order.status == OrderStatus.COMPLETED:
        raise BadRequestException("Заказ-наряд уже завершен")
    
    # Завершать можно только оплаченный заказ (списание только после оплаты)
    if order.status != OrderStatus.PAID:
        raise BadRequestException(
            "Завершить заказ можно только после полной оплаты. Статус «Готов к оплате» не гарантирует оплату."
        )
    
    # Проверяем наличие всех запчастей на складе перед списанием
    already_written = db.query(WarehouseTransaction).filter(
        WarehouseTransaction.order_id == order.id,
        WarehouseTransaction.transaction_type == TransactionType.OUTGOING,
    ).first() is not None
    
    if not already_written:
        missing = []
        for order_part in order.order_parts:
            if not order_part.part_id:
                continue
            warehouse_item = db.query(WarehouseItem).filter(WarehouseItem.part_id == order_part.part_id).first()
            label = order_part.article or order_part.part_name or str(order_part.part_id)
            if not warehouse_item:
                missing.append(f"{label}: отсутствует на складе")
            elif warehouse_item.quantity < order_part.quantity:
                need = order_part.quantity - warehouse_item.quantity
                missing.append(f"{label}: не хватает {need} шт. (на складе {warehouse_item.quantity})")
        if missing:
            raise BadRequestException(
                "Нельзя завершить заказ: недостаточно запчастей на складе. " + "; ".join(missing)
            )
        # Списываем запчасти (только при статусе PAID)
        for order_part in order.order_parts:
            if not order_part.part_id:
                continue
            warehouse_item = db.query(WarehouseItem).filter(WarehouseItem.part_id == order_part.part_id).first()
            warehouse_item.quantity -= order_part.quantity
            transaction = WarehouseTransaction(
                warehouse_item_id=warehouse_item.id,
                transaction_type=TransactionType.OUTGOING,
                quantity=order_part.quantity,
                price=order_part.price,
                order_id=order.id,
                employee_id=employee_id
            )
            db.add(transaction)
    
    order.status = OrderStatus.COMPLETED
    if not order.completed_at:
        order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order

