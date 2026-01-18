from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.warehouse import TransactionType
from app.schemas.part import Part


class WarehouseItemBase(BaseModel):
    part_id: int
    quantity: Decimal
    min_quantity: Decimal = 0
    location: Optional[str] = None


class WarehouseItemCreate(WarehouseItemBase):
    pass


class WarehouseItemUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    min_quantity: Optional[Decimal] = None
    location: Optional[str] = None


class WarehouseItem(WarehouseItemBase):
    id: int
    last_updated: datetime
    part: Part

    class Config:
        from_attributes = True


class WarehouseTransactionCreate(BaseModel):
    warehouse_item_id: int
    transaction_type: TransactionType
    quantity: Decimal
    price: Optional[Decimal] = None
    order_id: Optional[int] = None


class WarehouseTransaction(WarehouseTransactionCreate):
    id: int
    employee_id: int
    created_at: datetime

    class Config:
        from_attributes = True

