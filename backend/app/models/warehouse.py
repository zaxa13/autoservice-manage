from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TransactionType(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    ADJUSTMENT = "adjustment"


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
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    warehouse_item = relationship("WarehouseItem", back_populates="transactions")
    order = relationship("Order")
    employee = relationship("Employee", back_populates="warehouse_transactions")

