from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.models.warehouse import TransactionType
from app.schemas.part import Part


class WarehouseAdjustmentCreate(BaseModel):
    warehouse_item_id: int = Field(..., description="ID позиции на складе")
    quantity_delta: Decimal = Field(..., description="Изменение количества (положительное — приход, отрицательное — списание)")
    reason: Optional[str] = Field(None, description="Причина корректировки")


class WarehouseItemBase(BaseModel):
    part_id: int = Field(..., description="ID запчасти из справочника")
    quantity: Decimal = Field(..., ge=0, description="Текущее количество на складе")
    min_quantity: Decimal = Field(0, ge=0, description="Минимальный остаток (для уведомлений о нехватке)")
    location: Optional[str] = Field(None, description="Место хранения на складе")


class WarehouseItemCreate(WarehouseItemBase):
    pass


class WarehouseItemUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, ge=0, description="Количество")
    min_quantity: Optional[Decimal] = Field(None, ge=0, description="Минимальный остаток")
    location: Optional[str] = Field(None, description="Место хранения")


class WarehouseItem(WarehouseItemBase):
    id: int = Field(..., description="Уникальный ID позиции склада")
    last_updated: datetime = Field(..., description="Дата последнего обновления")
    part: Part = Field(..., description="Данные запчасти")

    class Config:
        from_attributes = True


class WarehouseTransactionCreate(BaseModel):
    warehouse_item_id: int = Field(..., description="ID позиции на складе")
    transaction_type: TransactionType = Field(..., description="Тип движения (incoming, outgoing, adjustment, return)")
    quantity: Decimal = Field(..., gt=0, description="Количество")
    price: Optional[Decimal] = Field(None, ge=0, description="Цена за единицу")
    order_id: Optional[int] = Field(None, description="ID заказ-наряда (для списания)")
    receipt_id: Optional[int] = Field(None, description="ID приходной накладной")


class WarehouseTransaction(WarehouseTransactionCreate):
    id: int = Field(..., description="Уникальный ID транзакции")
    employee_id: int = Field(..., description="ID сотрудника, выполнившего операцию")
    receipt_id: Optional[int] = Field(None, description="ID приходной накладной")
    created_at: datetime = Field(..., description="Дата и время операции")

    class Config:
        from_attributes = True


class WarehouseTransactionList(BaseModel):
    """Transaction with nested data for journal list."""
    id: int = Field(..., description="ID транзакции")
    warehouse_item_id: int = Field(..., description="ID позиции на складе")
    transaction_type: TransactionType = Field(..., description="Тип движения")
    quantity: Decimal = Field(..., description="Количество")
    price: Optional[Decimal] = Field(None, description="Цена за единицу")
    order_id: Optional[int] = Field(None, description="ID заказ-наряда")
    receipt_id: Optional[int] = Field(None, description="ID приходной накладной")
    employee_id: int = Field(..., description="ID сотрудника")
    created_at: datetime = Field(..., description="Дата и время операции")
    part: Optional[Part] = Field(None, description="Данные запчасти")
    order_number: Optional[str] = Field(None, description="Номер заказ-наряда")
    receipt_number: Optional[str] = Field(None, description="Номер приходной накладной")
    employee_name: Optional[str] = Field(None, description="ФИО сотрудника")

    class Config:
        from_attributes = True
