from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import enum
from app.database import Base


class TransactionType(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    ADJUSTMENT = "adjustment"


class ReceiptStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"


class ReceiptDocument(Base):
    __tablename__ = "receipt_documents"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    document_date = Column(Date, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    supplier_document_number = Column(String, nullable=True)
    supplier_document_date = Column(Date, nullable=True)
    status = Column(Enum(ReceiptStatus), nullable=False, default=ReceiptStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier", back_populates="receipt_documents")
    lines = relationship("ReceiptLine", back_populates="receipt", cascade="all, delete-orphan")
    transactions = relationship("WarehouseTransaction", back_populates="receipt")

    @property
    def total_amount(self):
        """Итоговая сумма накладной по закупочным ценам (quantity * purchase_price по строкам)."""
        return sum(
            (Decimal(line.quantity) * Decimal(line.purchase_price) for line in self.lines),
            Decimal(0),
        )


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipt_documents.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)

    receipt = relationship("ReceiptDocument", back_populates="lines")
    part = relationship("Part")


class WarehouseItem(Base):
    __tablename__ = "warehouse_items"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False, unique=True)
    quantity = Column(Numeric(10, 2), nullable=False, default=0)
    min_quantity = Column(Numeric(10, 2), nullable=False, default=0)
    location = Column(String, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    part = relationship("Part")
    transactions = relationship("WarehouseTransaction", back_populates="warehouse_item")


class WarehouseTransaction(Base):
    __tablename__ = "warehouse_transactions"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_item_id = Column(Integer, ForeignKey("warehouse_items.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    receipt_id = Column(Integer, ForeignKey("receipt_documents.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    warehouse_item = relationship("WarehouseItem", back_populates="transactions")
    order = relationship("Order")
    receipt = relationship("ReceiptDocument", back_populates="transactions")
    employee = relationship("Employee", back_populates="warehouse_transactions")

