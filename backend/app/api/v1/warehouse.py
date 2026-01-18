from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.warehouse import (
    WarehouseItem as WarehouseItemSchema,
    WarehouseItemCreate,
    WarehouseItemUpdate,
    WarehouseTransaction as WarehouseTransactionSchema,
    WarehouseTransactionCreate
)
from app.services.warehouse_service import (
    create_warehouse_item,
    add_incoming_transaction,
    get_low_stock_items
)
from app.core.permissions import require_manager_or_admin

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

