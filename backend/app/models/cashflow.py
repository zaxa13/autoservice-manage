from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class AccountType(str, enum.Enum):
    CASH = "cash"       # Наличные (физическая касса)
    BANK = "bank"       # Банковский расчётный счёт


class TransactionType(str, enum.Enum):
    INCOME = "income"       # Приход
    EXPENSE = "expense"     # Расход
    TRANSFER = "transfer"   # Перевод между счетами


class Account(Base):
    """Счёт / регистр денежных средств (касса, банковский счёт)."""

    __tablename__ = "cash_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    account_type = Column(
        Enum(AccountType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    initial_balance = Column(Numeric(12, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transactions_from = relationship(
        "CashTransaction",
        foreign_keys="CashTransaction.account_id",
        back_populates="account",
    )
    transactions_to = relationship(
        "CashTransaction",
        foreign_keys="CashTransaction.to_account_id",
        back_populates="to_account",
    )


class TransactionCategory(Base):
    """Категория операции (Оплата заказа, Зарплата, Аренда, Закупка и т.д.)."""

    __tablename__ = "cash_transaction_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    transaction_type = Column(
        Enum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    transactions = relationship("CashTransaction", back_populates="category")


class CashTransaction(Base):
    """Операция движения денежных средств."""

    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(
        Enum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    account_id = Column(Integer, ForeignKey("cash_accounts.id"), nullable=False)
    # Для операций типа transfer — счёт назначения
    to_account_id = Column(Integer, ForeignKey("cash_accounts.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("cash_transaction_categories.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Опциональные привязки к другим сущностям
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    salary_id = Column(Integer, ForeignKey("salaries.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)

    account = relationship("Account", foreign_keys=[account_id], back_populates="transactions_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_to")
    category = relationship("TransactionCategory", back_populates="transactions")
    order = relationship("Order")
    salary = relationship("Salary")
    payment = relationship("Payment")
