from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, datetime, time
from app.models.warehouse import (
    WarehouseItem,
    WarehouseTransaction,
    TransactionType,
    ReceiptDocument,
    ReceiptLine,
    ReceiptStatus,
)
from app.models.part import Part
from app.models.order import Order
from app.models.employee import Employee
from app.schemas.warehouse import (
    WarehouseItemCreate,
    WarehouseTransactionCreate,
    WarehouseAdjustmentCreate,
)
from app.schemas.receipt import ReceiptDocumentCreate
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
        receipt_id=transaction_create.receipt_id if hasattr(transaction_create, "receipt_id") else None,
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


def generate_receipt_number(db: Session) -> str:
    """Генерация уникального номера приходной накладной"""
    today = datetime.now().strftime("%Y%m%d")
    last_rec = (
        db.query(ReceiptDocument)
        .filter(ReceiptDocument.number.like(f"REC-{today}-%"))
        .order_by(ReceiptDocument.number.desc())
        .first()
    )
    if last_rec:
        last_num = int(last_rec.number.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    return f"REC-{today}-{new_num:04d}"


def create_receipt_document(db: Session, payload: ReceiptDocumentCreate) -> ReceiptDocument:
    """Создание приходной накладной (черновик)."""
    number = generate_receipt_number(db)
    receipt = ReceiptDocument(
        number=number,
        document_date=payload.document_date,
        supplier_id=payload.supplier_id,
        supplier_document_number=payload.supplier_document_number,
        supplier_document_date=payload.supplier_document_date or payload.document_date,
        status=ReceiptStatus.DRAFT,
    )
    db.add(receipt)
    db.flush()
    for line in payload.lines:
        rl = ReceiptLine(
            receipt_id=receipt.id,
            part_id=line.part_id,
            quantity=line.quantity,
            purchase_price=line.purchase_price,
            sale_price=line.sale_price,
        )
        db.add(rl)
    db.commit()
    db.refresh(receipt)
    return receipt


def post_receipt_document(db: Session, receipt_id: int, employee_id: int) -> ReceiptDocument:
    """Проведение приходной накладной: обновление остатков и создание транзакций."""
    receipt = db.query(ReceiptDocument).filter(ReceiptDocument.id == receipt_id).first()
    if not receipt:
        raise NotFoundException("Накладная не найдена")
    if receipt.status == ReceiptStatus.POSTED:
        raise BadRequestException("Накладная уже проведена")
    if not receipt.lines:
        raise BadRequestException("Накладная не содержит строк")

    for line in receipt.lines:
        part = db.query(Part).filter(Part.id == line.part_id).first()
        if not part:
            raise NotFoundException(f"Запчасть id={line.part_id} не найдена")

        warehouse_item = db.query(WarehouseItem).filter(WarehouseItem.part_id == line.part_id).first()
        if not warehouse_item:
            warehouse_item = WarehouseItem(
                part_id=line.part_id,
                quantity=Decimal(0),
                min_quantity=Decimal(0),
            )
            db.add(warehouse_item)
            db.flush()

        warehouse_item.quantity += line.quantity

        trans = WarehouseTransaction(
            warehouse_item_id=warehouse_item.id,
            transaction_type=TransactionType.INCOMING,
            quantity=line.quantity,
            price=line.purchase_price,
            receipt_id=receipt.id,
            employee_id=employee_id,
        )
        db.add(trans)

        part.price = line.sale_price
        part.purchase_price_last = line.purchase_price

    receipt.status = ReceiptStatus.POSTED
    db.commit()
    db.refresh(receipt)
    return receipt


def get_supplier_receipts_report(
    db: Session,
    supplier_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Отчёт по приходным накладным поставщика за период (по document_date)."""
    from sqlalchemy.orm import joinedload
    from app.models.supplier import Supplier

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise NotFoundException("Поставщик не найден")

    q = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
            joinedload(ReceiptDocument.supplier),
        )
        .filter(ReceiptDocument.supplier_id == supplier_id)
    )
    if date_from is not None:
        q = q.filter(ReceiptDocument.document_date >= date_from)
    if date_to is not None:
        q = q.filter(ReceiptDocument.document_date <= date_to)
    q = q.order_by(ReceiptDocument.document_date.asc(), ReceiptDocument.id.asc())
    receipts = q.all()

    total_amount = sum((r.total_amount or Decimal(0)) for r in receipts)
    return {
        "receipts": receipts,
        "total_count": len(receipts),
        "total_amount": total_amount,
    }


def get_transactions(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    transaction_type: TransactionType | None = None,
    part_id: int | None = None,
    order_id: int | None = None,
    receipt_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list:
    """Список транзакций склада с фильтрами для журнала движений."""
    q = db.query(WarehouseTransaction).join(WarehouseItem)
    if date_from is not None:
        q = q.filter(WarehouseTransaction.created_at >= date_from)
    if date_to is not None:
        end_of_day = datetime.combine(date_to, time.max)
        q = q.filter(WarehouseTransaction.created_at <= end_of_day)
    if transaction_type is not None:
        q = q.filter(WarehouseTransaction.transaction_type == transaction_type)
    if part_id is not None:
        q = q.filter(WarehouseItem.part_id == part_id)
    if order_id is not None:
        q = q.filter(WarehouseTransaction.order_id == order_id)
    if receipt_id is not None:
        q = q.filter(WarehouseTransaction.receipt_id == receipt_id)
    q = q.order_by(WarehouseTransaction.created_at.desc()).offset(skip).limit(limit)
    rows = q.all()
    out = []
    for t in rows:
        part = t.warehouse_item.part if t.warehouse_item else None
        order_number = t.order.number if t.order else None
        receipt_number = t.receipt.number if t.receipt else None
        employee_name = t.employee.full_name if t.employee else None
        out.append({
            "id": t.id,
            "warehouse_item_id": t.warehouse_item_id,
            "transaction_type": t.transaction_type,
            "quantity": t.quantity,
            "price": t.price,
            "order_id": t.order_id,
            "receipt_id": t.receipt_id,
            "employee_id": t.employee_id,
            "created_at": t.created_at,
            "part": part,
            "order_number": order_number,
            "receipt_number": receipt_number,
            "employee_name": employee_name,
        })
    return out


def create_adjustment(
    db: Session,
    payload: WarehouseAdjustmentCreate,
    employee_id: int,
) -> WarehouseTransaction:
    """Ручная корректировка остатка по позиции склада."""
    item = db.query(WarehouseItem).filter(WarehouseItem.id == payload.warehouse_item_id).first()
    if not item:
        raise NotFoundException("Позиция склада не найдена")
    new_qty = item.quantity + payload.quantity_delta
    if new_qty < 0:
        raise BadRequestException("Остаток не может стать отрицательным")
    item.quantity = new_qty
    trans = WarehouseTransaction(
        warehouse_item_id=item.id,
        transaction_type=TransactionType.ADJUSTMENT,
        quantity=payload.quantity_delta,
        price=None,
        order_id=None,
        receipt_id=None,
        employee_id=employee_id,
    )
    db.add(trans)
    db.commit()
    db.refresh(trans)
    return trans

