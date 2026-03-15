from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.warehouse import ReceiptStatus
from app.schemas.part import Part
from app.schemas.supplier import Supplier


class ReceiptLineBase(BaseModel):
    part_id: int
    quantity: Decimal
    purchase_price: Decimal
    sale_price: Decimal


class ReceiptLineCreate(ReceiptLineBase):
    pass


class ReceiptLine(ReceiptLineBase):
    id: int
    receipt_id: int
    part: Optional[Part] = None

    class Config:
        from_attributes = True


class ReceiptDocumentBase(BaseModel):
    document_date: date
    supplier_id: Optional[int] = None
    supplier_document_number: Optional[str] = None
    supplier_document_date: Optional[date] = None


class ReceiptDocumentCreate(ReceiptDocumentBase):
    lines: List[ReceiptLineCreate]


class ReceiptDocumentUpdate(BaseModel):
    document_date: Optional[date] = None
    supplier_id: Optional[int] = None
    supplier_document_number: Optional[str] = None
    supplier_document_date: Optional[date] = None
    lines: Optional[List[ReceiptLineCreate]] = None


class ReceiptDocument(ReceiptDocumentBase):
    id: int
    number: str
    status: ReceiptStatus
    created_at: datetime
    supplier: Optional[Supplier] = None
    lines: List[ReceiptLine] = []
    total_amount: Optional[Decimal] = None  # сумма по строкам (quantity * purchase_price)

    class Config:
        from_attributes = True


class SupplierReceiptsReport(BaseModel):
    """Отчёт по приходу от поставщика за период."""
    receipts: List[ReceiptDocument] = []
    total_count: int = 0
    total_amount: Decimal = Decimal("0")
