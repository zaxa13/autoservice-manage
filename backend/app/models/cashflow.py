"""Учёт денежных средств: счета (касса/банк), категории, транзакции.

Системные категории (`is_system=True`) копируются в каждого тенанта при
онбординге — глобально шарить мы их не можем (RLS изоляция).
"""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, TenantMixin


class AccountType(str, enum.Enum):
    CASH = "cash"
    BANK = "bank"


class CashflowTransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


# Alias для обратной совместимости со schemas/cashflow.py.
# В warehouse.py живёт другой `TransactionType` (incoming/outgoing/adjustment) —
# не путать.
TransactionType = CashflowTransactionType


class Account(Base, TenantMixin):
    __tablename__ = "cash_accounts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)


class TransactionCategory(Base, TenantMixin):
    __tablename__ = "cash_transaction_categories"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (PrimaryKeyConstraint("tenant_id", "id"),)


class CashTransaction(Base, TenantMixin):
    __tablename__ = "cash_transactions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_account_id: Mapped[int | None] = mapped_column(BigInteger)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    salary_id: Mapped[int | None] = mapped_column(BigInteger)
    payment_id: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["cash_accounts.tenant_id", "cash_accounts.id"],
            ondelete="RESTRICT",
            name="fk_cash_transactions_account",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "to_account_id"],
            ["cash_accounts.tenant_id", "cash_accounts.id"],
            ondelete="RESTRICT",
            name="fk_cash_transactions_to_account",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "category_id"],
            ["cash_transaction_categories.tenant_id", "cash_transaction_categories.id"],
            ondelete="RESTRICT",
            name="fk_cash_transactions_category",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="SET NULL",
            name="fk_cash_transactions_order",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "salary_id"],
            ["salaries.tenant_id", "salaries.id"],
            ondelete="SET NULL",
            name="fk_cash_transactions_salary",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["payments.tenant_id", "payments.id"],
            ondelete="SET NULL",
            name="fk_cash_transactions_payment",
        ),
        Index("ix_cash_transactions_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_cash_transactions_tenant_account", "tenant_id", "account_id"),
    )
