"""Склад: приходные документы, строки прихода, складская карточка, движения."""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class TransactionType(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    ADJUSTMENT = "adjustment"


class ReceiptStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"


class ReceiptDocument(Base, TenantMixin):
    __tablename__ = "receipt_documents"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    document_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(BigInteger)
    supplier_document_number: Mapped[str | None] = mapped_column(String(100))
    supplier_document_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReceiptStatus.DRAFT.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "number", name="uq_receipt_documents_tenant_number"),
        ForeignKeyConstraint(
            ["tenant_id", "supplier_id"],
            ["suppliers.tenant_id", "suppliers.id"],
            ondelete="SET NULL",
            name="fk_receipt_documents_supplier",
        ),
        Index("ix_receipt_documents_tenant_date", "tenant_id", "document_date"),
    )


class ReceiptLine(Base, TenantMixin):
    __tablename__ = "receipt_lines"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    receipt_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "receipt_id"],
            ["receipt_documents.tenant_id", "receipt_documents.id"],
            ondelete="CASCADE",
            name="fk_receipt_lines_receipt",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "part_id"],
            ["parts.tenant_id", "parts.id"],
            ondelete="RESTRICT",
            name="fk_receipt_lines_part",
        ),
        Index("ix_receipt_lines_tenant_receipt", "tenant_id", "receipt_id"),
    )


class WarehouseItem(Base, TenantMixin):
    __tablename__ = "warehouse_items"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(100))
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        # Одна складская карточка на одну запчасть в рамках тенанта.
        UniqueConstraint("tenant_id", "part_id", name="uq_warehouse_items_tenant_part"),
        ForeignKeyConstraint(
            ["tenant_id", "part_id"],
            ["parts.tenant_id", "parts.id"],
            ondelete="RESTRICT",
            name="fk_warehouse_items_part",
        ),
    )


class WarehouseTransaction(Base, TenantMixin):
    __tablename__ = "warehouse_transactions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    warehouse_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "warehouse_item_id"],
            ["warehouse_items.tenant_id", "warehouse_items.id"],
            ondelete="RESTRICT",
            name="fk_warehouse_transactions_item",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="SET NULL",
            name="fk_warehouse_transactions_order",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "receipt_id"],
            ["receipt_documents.tenant_id", "receipt_documents.id"],
            ondelete="SET NULL",
            name="fk_warehouse_transactions_receipt",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employees.tenant_id", "employees.id"],
            ondelete="RESTRICT",
            name="fk_warehouse_transactions_employee",
        ),
        Index("ix_warehouse_transactions_tenant_item", "tenant_id", "warehouse_item_id"),
        Index("ix_warehouse_transactions_tenant_created", "tenant_id", "created_at"),
    )
