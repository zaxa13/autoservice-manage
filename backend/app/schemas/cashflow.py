from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.cashflow import AccountType, TransactionType

__all__ = [
    "AccountCreate", "AccountUpdate", "AccountResponse",
    "TransactionCategoryCreate", "TransactionCategoryResponse",
    "CashTransactionCreate", "CashTransactionUpdate", "CashTransactionResponse",
    "CashflowSummary", "CashflowListResponse",
    "AccountShort", "CategoryShort",
]


# ── Account ───────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Название счёта", example="Касса (наличные)")
    account_type: AccountType = Field(..., description="Тип счёта: cash — наличные, bank — банковский счёт")
    initial_balance: Decimal = Field(Decimal("0"), ge=0, description="Начальный остаток при создании счёта")


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128, description="Новое название счёта")
    is_active: Optional[bool] = Field(None, description="Активность счёта")


class AccountResponse(BaseModel):
    id: int = Field(..., description="ID счёта")
    name: str = Field(..., description="Название счёта")
    account_type: AccountType = Field(..., description="Тип счёта")
    initial_balance: Decimal = Field(..., description="Начальный остаток")
    current_balance: Decimal = Field(..., description="Текущий остаток (начальный ± все операции)")
    is_active: bool = Field(..., description="Активен ли счёт")
    created_at: datetime = Field(..., description="Дата создания")

    class Config:
        from_attributes = True


# ── TransactionCategory ───────────────────────────────────────────────────────

class TransactionCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Название категории", example="Аренда")
    transaction_type: TransactionType = Field(..., description="Тип: income, expense или transfer")


class TransactionCategoryResponse(BaseModel):
    id: int = Field(..., description="ID категории")
    name: str = Field(..., description="Название категории")
    transaction_type: TransactionType = Field(..., description="Тип операции")
    is_system: bool = Field(..., description="Системная категория (не удаляется)")
    is_active: bool = Field(..., description="Активна ли категория")

    class Config:
        from_attributes = True


# ── CashTransaction ───────────────────────────────────────────────────────────

class CashTransactionUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, description="Новая сумма операции")
    description: Optional[str] = Field(None, max_length=512, description="Новое описание")
    transaction_date: Optional[datetime] = Field(None, description="Новая дата операции")
    category_id: Optional[int] = Field(None, description="Новая категория (того же типа)")


class CashTransactionCreate(BaseModel):
    transaction_type: TransactionType = Field(..., description="Тип операции: income, expense, transfer")
    account_id: int = Field(..., description="ID счёта списания/поступления")
    to_account_id: Optional[int] = Field(
        None, description="ID счёта назначения (только для transfer)"
    )
    category_id: int = Field(..., description="ID категории операции")
    amount: Decimal = Field(..., gt=0, description="Сумма операции")
    description: Optional[str] = Field(None, max_length=512, description="Описание / комментарий")
    transaction_date: Optional[datetime] = Field(None, description="Дата операции (по умолчанию — сейчас)")
    order_id: Optional[int] = Field(None, description="Привязка к заказ-наряду")
    salary_id: Optional[int] = Field(None, description="Привязка к расчёту зарплаты")


class AccountShort(BaseModel):
    id: int
    name: str
    account_type: AccountType

    class Config:
        from_attributes = True


class CategoryShort(BaseModel):
    id: int
    name: str
    transaction_type: TransactionType

    class Config:
        from_attributes = True


class CashTransactionResponse(BaseModel):
    id: int = Field(..., description="ID операции")
    transaction_type: TransactionType = Field(..., description="Тип операции")
    account_id: int = Field(..., description="ID счёта")
    account: AccountShort = Field(..., description="Счёт")
    to_account_id: Optional[int] = Field(None, description="ID счёта назначения (для переводов)")
    to_account: Optional[AccountShort] = Field(None, description="Счёт назначения (для переводов)")
    category_id: int = Field(..., description="ID категории")
    category: CategoryShort = Field(..., description="Категория")
    amount: Decimal = Field(..., description="Сумма")
    description: Optional[str] = Field(None, description="Описание")
    transaction_date: datetime = Field(..., description="Дата операции")
    created_at: datetime = Field(..., description="Дата создания записи")
    order_id: Optional[int] = Field(None, description="ID связанного заказа")
    salary_id: Optional[int] = Field(None, description="ID связанной выплаты зарплаты")

    class Config:
        from_attributes = True


# ── Dashboard / Summary ───────────────────────────────────────────────────────

class CashflowSummary(BaseModel):
    total_balance: Decimal = Field(..., description="Суммарный остаток по всем активным счетам")
    total_income: Decimal = Field(..., description="Сумма всех приходов за период")
    total_expense: Decimal = Field(..., description="Сумма всех расходов за период")
    net_flow: Decimal = Field(..., description="Чистый денежный поток (приход − расход) за период")
    accounts: List[AccountResponse] = Field(..., description="Остатки по каждому счёту")


class CashflowListResponse(BaseModel):
    total: int = Field(..., description="Общее количество операций (без пагинации)")
    items: List[CashTransactionResponse] = Field(..., description="Список операций")
