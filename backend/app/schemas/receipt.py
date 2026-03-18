from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.warehouse import ReceiptStatus
from app.schemas.part import Part
from app.schemas.supplier import Supplier


class ReceiptLineBase(BaseModel):
    part_id: int = Field(..., description="ID запчасти из справочника")
    quantity: Decimal = Field(..., gt=0, description="Количество")
    purchase_price: Decimal = Field(..., ge=0, description="Закупочная цена за единицу")
    sale_price: Decimal = Field(..., ge=0, description="Цена продажи за единицу")


class ReceiptLineCreate(ReceiptLineBase):
    pass


class ReceiptLine(ReceiptLineBase):
    id: int = Field(..., description="ID строки накладной")
    receipt_id: int = Field(..., description="ID накладной")
    part: Optional[Part] = Field(None, description="Данные запчасти")

    class Config:
        from_attributes = True


class ReceiptDocumentBase(BaseModel):
    document_date: date = Field(..., description="Дата документа")
    supplier_id: Optional[int] = Field(None, description="ID поставщика")
    supplier_document_number: Optional[str] = Field(None, description="Номер документа поставщика")
    supplier_document_date: Optional[date] = Field(None, description="Дата документа поставщика")


class ReceiptDocumentCreate(ReceiptDocumentBase):
    lines: List[ReceiptLineCreate] = Field(..., min_length=1, description="Строки накладной (минимум одна)")


class ReceiptDocumentUpdate(BaseModel):
    document_date: Optional[date] = Field(None, description="Дата документа")
    supplier_id: Optional[int] = Field(None, description="ID поставщика")
    supplier_document_number: Optional[str] = Field(None, description="Номер документа поставщика")
    supplier_document_date: Optional[date] = Field(None, description="Дата документа поставщика")
    lines: Optional[List[ReceiptLineCreate]] = Field(None, description="Обновлённые строки накладной (заменяют все существующие)")


class ReceiptDocument(ReceiptDocumentBase):
    id: int = Field(..., description="Уникальный ID накладной")
    number: str = Field(..., description="Номер накладной")
    status: ReceiptStatus = Field(..., description="Статус (draft / posted)")
    created_at: datetime = Field(..., description="Дата создания")
    supplier: Optional[Supplier] = Field(None, description="Данные поставщика")
    lines: List[ReceiptLine] = Field(default_factory=list, description="Строки накладной")
    total_amount: Optional[Decimal] = Field(None, description="Итого по накладной (quantity × purchase_price)")

    class Config:
        from_attributes = True


class SupplierReceiptsReport(BaseModel):
    """Отчёт по приходу от поставщика за период."""
    receipts: List[ReceiptDocument] = Field(default_factory=list, description="Список накладных")
    total_count: int = Field(0, description="Общее количество накладных")
    total_amount: Decimal = Field(Decimal("0"), description="Общая сумма по накладным")
