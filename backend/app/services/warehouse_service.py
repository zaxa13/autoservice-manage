from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.warehouse import WarehouseItem, WarehouseTransaction, TransactionType
from app.models.part import Part
from app.schemas.warehouse import WarehouseItemCreate, WarehouseTransactionCreate
from app.core.exceptions import NotFoundException, BadRequestException


def create_warehouse_item(db: Session, item_create: WarehouseItemCreate) -> WarehouseItem:
    """Создание позиции на складе"""
    # Проверка существования запчасти
    part = db.query(Part).filter(Part.id == item_create.part_id).first()
    if not part:
        raise NotFoundException("Запчасть не найдена")
    
    # Проверка существования позиции
    existing = db.query(WarehouseItem).filter(WarehouseItem.part_id == item_create.part_id).first()
    if existing:
        raise BadRequestException("Позиция для этой запчасти уже существует")
    
    warehouse_item = WarehouseItem(
        part_id=item_create.part_id,
        quantity=item_create.quantity,
        min_quantity=item_create.min_quantity,
        location=item_create.location
    )
    db.add(warehouse_item)
    db.commit()
    db.refresh(warehouse_item)
    return warehouse_item


def add_incoming_transaction(
    db: Session,
    transaction_create: WarehouseTransactionCreate,
    employee_id: int
) -> WarehouseTransaction:
    """Приход на склад"""
    warehouse_item = db.query(WarehouseItem).filter(
        WarehouseItem.id == transaction_create.warehouse_item_id
    ).first()
    
    if not warehouse_item:
        raise NotFoundException("Позиция склада не найдена")
    
    if transaction_create.transaction_type != TransactionType.INCOMING:
        raise BadRequestException("Тип транзакции должен быть incoming")
    
    # Увеличиваем количество
    warehouse_item.quantity += transaction_create.quantity
    
    # Создаем транзакцию
    transaction = WarehouseTransaction(
        warehouse_item_id=warehouse_item.id,
        transaction_type=TransactionType.INCOMING,
        quantity=transaction_create.quantity,
        price=transaction_create.price,
        order_id=transaction_create.order_id,
        employee_id=employee_id
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_low_stock_items(db: Session) -> list:
    """Получение позиций с низким остатком"""
    items = db.query(WarehouseItem).filter(
        WarehouseItem.quantity <= WarehouseItem.min_quantity
    ).all()
    return items

