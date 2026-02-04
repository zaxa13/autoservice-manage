from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.warehouse import ReceiptDocument, ReceiptLine, ReceiptStatus, TransactionType
from app.schemas.warehouse import (
    WarehouseItem as WarehouseItemSchema,
    WarehouseItemCreate,
    WarehouseItemUpdate,
    WarehouseTransaction as WarehouseTransactionSchema,
    WarehouseTransactionCreate,
    WarehouseTransactionList,
    WarehouseAdjustmentCreate,
)
from app.schemas.receipt import ReceiptDocument as ReceiptDocumentSchema, ReceiptDocumentCreate, ReceiptDocumentUpdate
from app.services.warehouse_service import (
    create_warehouse_item,
    add_incoming_transaction,
    get_low_stock_items,
    create_receipt_document,
    post_receipt_document,
    get_transactions,
    create_adjustment,
)
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter()


@router.get("/items", response_model=List[WarehouseItemSchema])
def get_warehouse_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка позиций склада"""
    from app.models.warehouse import WarehouseItem
    items = db.query(WarehouseItem).offset(skip).limit(limit).all()
    return items


@router.get("/items/{item_id}", response_model=WarehouseItemSchema)
def get_warehouse_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение позиции склада по ID"""
    from app.models.warehouse import WarehouseItem
    from app.core.exceptions import NotFoundException
    
    item = db.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
    if not item:
        raise NotFoundException("Позиция склада не найдена")
    return item


@router.post("/items", response_model=WarehouseItemSchema)
def create_item(
    item_create: WarehouseItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание позиции на складе"""
    item = create_warehouse_item(db, item_create)
    return item


@router.post("/transactions/incoming", response_model=WarehouseTransactionSchema)
def create_incoming_transaction(
    transaction_create: WarehouseTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Приход на склад"""
    if not current_user.employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    
    transaction = add_incoming_transaction(db, transaction_create, current_user.employee_id)
    return transaction


@router.get("/low-stock", response_model=List[WarehouseItemSchema])
def get_low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение позиций с низким остатком"""
    items = get_low_stock_items(db)
    return items


@router.get("/transactions", response_model=List[WarehouseTransactionList])
def list_transactions(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None,
    part_id: Optional[int] = None,
    order_id: Optional[int] = None,
    receipt_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Журнал движений склада."""
    return get_transactions(
        db,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        part_id=part_id,
        order_id=order_id,
        receipt_id=receipt_id,
        skip=skip,
        limit=limit,
    )


@router.post("/transactions/adjustment", response_model=WarehouseTransactionSchema)
def adjustment(
    payload: WarehouseAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Ручная корректировка остатка."""
    if not current_user.employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    return create_adjustment(db, payload, current_user.employee_id)


@router.get("/receipts", response_model=List[ReceiptDocumentSchema])
def list_receipts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ReceiptStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список приходных накладных (с подгрузкой строк для итога)."""
    from sqlalchemy.orm import joinedload
    q = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
        )
        .order_by(ReceiptDocument.created_at.desc())
    )
    if status is not None:
        q = q.filter(ReceiptDocument.status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/receipts/{receipt_id}", response_model=ReceiptDocumentSchema)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Приходная накладная по ID."""
    from sqlalchemy.orm import joinedload
    r = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
        )
        .filter(ReceiptDocument.id == receipt_id)
        .first()
    )
    if not r:
        raise NotFoundException("Накладная не найдена")
    return r


@router.post("/receipts", response_model=ReceiptDocumentSchema)
def create_receipt(
    payload: ReceiptDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Создание приходной накладной (черновик)."""
    return create_receipt_document(db, payload)


@router.put("/receipts/{receipt_id}", response_model=ReceiptDocumentSchema)
def update_receipt(
    receipt_id: int,
    payload: ReceiptDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Обновление черновика накладной."""
    r = db.query(ReceiptDocument).filter(ReceiptDocument.id == receipt_id).first()
    if not r:
        raise NotFoundException("Накладная не найдена")
    if r.status != ReceiptStatus.DRAFT:
        raise BadRequestException("Можно редактировать только черновик")
    if payload.document_date is not None:
        r.document_date = payload.document_date
    if payload.supplier_id is not None:
        r.supplier_id = payload.supplier_id
    if payload.lines is not None:
        from app.models.warehouse import ReceiptLine
        db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt_id).delete()
        for line in payload.lines:
            rl = ReceiptLine(
                receipt_id=r.id,
                part_id=line.part_id,
                quantity=line.quantity,
                purchase_price=line.purchase_price,
                sale_price=line.sale_price,
            )
            db.add(rl)
    db.commit()
    db.refresh(r)
    return r


@router.post("/receipts/{receipt_id}/post", response_model=ReceiptDocumentSchema)
def post_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Проведение приходной накладной."""
    if not current_user.employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    return post_receipt_document(db, receipt_id, current_user.employee_id)

