"""Касса и денежные потоки — async CRUD на shared-DB.

Три ресурса: счета (accounts), категории (categories), операции (transactions).
Плюс summary-эндпоинт.

Балансы счетов считаются на лету: initial_balance + ΣIncome + Σ(transfers IN)
− ΣExpense − Σ(transfers OUT).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import require_accountant_or_admin, require_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.cashflow import (
    Account,
    CashflowTransactionType,
    CashTransaction,
    TransactionCategory,
)
from app.schemas.cashflow import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    CashTransactionCreate,
    CashTransactionResponse,
    CashTransactionUpdate,
    CashflowListResponse,
    CashflowSummary,
    TransactionCategoryCreate,
    TransactionCategoryResponse,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_auth = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Только бухгалтер / администратор"},
}
_404 = {404: {"model": ErrorResponse, "description": "Объект не найден"}}
_400 = {400: {"model": ErrorResponse, "description": "Некорректные данные"}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _balance(db: AsyncSession, account_id: int, initial: Decimal) -> Decimal:
    """initial_balance + ΣIncome + Σ(transfers IN) − ΣExpense − Σ(transfers OUT)."""
    stmt = text(
        """
        SELECT
          COALESCE(SUM(CASE WHEN transaction_type='income'   AND account_id   = :aid THEN amount END), 0)
        + COALESCE(SUM(CASE WHEN transaction_type='transfer' AND to_account_id= :aid THEN amount END), 0)
        - COALESCE(SUM(CASE WHEN transaction_type='expense'  AND account_id   = :aid THEN amount END), 0)
        - COALESCE(SUM(CASE WHEN transaction_type='transfer' AND account_id   = :aid THEN amount END), 0)
        FROM app.cash_transactions
        WHERE account_id = :aid OR to_account_id = :aid
        """
    )
    delta = (await db.execute(stmt, {"aid": account_id})).scalar() or Decimal(0)
    return Decimal(initial) + Decimal(delta)


async def _serialize_account(db: AsyncSession, a: Account) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "account_type": a.account_type,
        "initial_balance": a.initial_balance,
        "current_balance": await _balance(db, a.id, a.initial_balance),
        "is_active": a.is_active,
        "created_at": a.created_at,
    }


async def _serialize_transaction(
    db: AsyncSession, t: CashTransaction, claims: TenantClaims
) -> dict:
    account = await db.get(Account, (claims.tenant_id, t.account_id))
    to_account = (
        await db.get(Account, (claims.tenant_id, t.to_account_id))
        if t.to_account_id else None
    )
    category = await db.get(TransactionCategory, (claims.tenant_id, t.category_id))

    def _short(a: Account | None) -> dict | None:
        if a is None:
            return None
        return {"id": a.id, "name": a.name, "account_type": a.account_type}

    return {
        "id": t.id,
        "transaction_type": t.transaction_type,
        "account_id": t.account_id,
        "account": _short(account),
        "to_account_id": t.to_account_id,
        "to_account": _short(to_account),
        "category_id": t.category_id,
        "category": (
            {"id": category.id, "name": category.name,
             "transaction_type": category.transaction_type}
            if category else None
        ),
        "amount": t.amount,
        "description": t.description,
        "transaction_date": t.transaction_date,
        "created_at": t.created_at,
        "order_id": t.order_id,
        "salary_id": t.salary_id,
    }


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
@router.get("/accounts", response_model=list[AccountResponse], responses=_auth, tags=["Касса — счета"])
async def list_accounts(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(require_accountant_or_admin),
):
    stmt = select(Account).order_by(Account.id)
    if not include_inactive:
        stmt = stmt.where(Account.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return [await _serialize_account(db, a) for a in rows]


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**_auth, **_400},
    tags=["Касса — счета"],
)
async def create_account_ep(
    body: AccountCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    a = Account(
        tenant_id=claims.tenant_id,
        name=body.name,
        account_type=body.account_type.value,
        initial_balance=body.initial_balance,
        is_active=True,
    )
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return await _serialize_account(db, a)


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    responses={**_auth, **_404},
    tags=["Касса — счета"],
)
async def get_account_ep(
    account_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    a = await db.get(Account, (claims.tenant_id, account_id))
    if a is None:
        raise NotFoundException("Счёт не найден")
    return await _serialize_account(db, a)


@router.patch(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    responses={**_auth, **_404},
    tags=["Касса — счета"],
)
async def update_account_ep(
    account_id: int,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    a = await db.get(Account, (claims.tenant_id, account_id))
    if a is None:
        raise NotFoundException("Счёт не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    await db.flush()
    await db.refresh(a)
    return await _serialize_account(db, a)


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_auth, **_404, **_400},
    tags=["Касса — счета"],
)
async def delete_account_ep(
    account_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
) -> Response:
    a = await db.get(Account, (claims.tenant_id, account_id))
    if a is None:
        raise NotFoundException("Счёт не найден")
    # Запрет удаления при наличии транзакций.
    cnt = (await db.execute(
        select(func.count()).select_from(CashTransaction).where(
            (CashTransaction.account_id == account_id) |
            (CashTransaction.to_account_id == account_id)
        )
    )).scalar()
    if cnt:
        raise BadRequestException(
            "Нельзя удалить счёт с историей операций — деактивируйте его"
        )
    await db.delete(a)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@router.get(
    "/categories",
    response_model=list[TransactionCategoryResponse],
    responses=_auth,
    tags=["Касса — категории"],
)
async def list_categories(
    transaction_type: Optional[CashflowTransactionType] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(require_accountant_or_admin),
):
    stmt = select(TransactionCategory).where(TransactionCategory.is_active.is_(True)).order_by(TransactionCategory.id)
    if transaction_type:
        stmt = stmt.where(TransactionCategory.transaction_type == transaction_type.value)
    return list((await db.execute(stmt)).scalars().all())


@router.post(
    "/categories",
    response_model=TransactionCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**_auth, **_400},
    tags=["Касса — категории"],
)
async def create_category_ep(
    body: TransactionCategoryCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    cat = TransactionCategory(
        tenant_id=claims.tenant_id,
        name=body.name,
        transaction_type=body.transaction_type.value,
        is_system=False,
        is_active=True,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_auth, **_404, **_400},
    tags=["Касса — категории"],
)
async def delete_category_ep(
    category_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
) -> Response:
    cat = await db.get(TransactionCategory, (claims.tenant_id, category_id))
    if cat is None:
        raise NotFoundException("Категория не найдена")
    if cat.is_system:
        raise BadRequestException("Системная категория не может быть удалена")
    cnt = (await db.execute(
        select(func.count()).select_from(CashTransaction).where(
            CashTransaction.category_id == category_id
        )
    )).scalar()
    if cnt:
        raise BadRequestException("Нельзя удалить категорию с привязанными операциями")
    await db.delete(cat)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
@router.get(
    "/transactions",
    response_model=CashflowListResponse,
    responses=_auth,
    tags=["Касса — операции"],
)
async def list_transactions(
    account_id: Optional[int] = Query(None),
    transaction_type: Optional[CashflowTransactionType] = Query(None),
    category_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    base = select(CashTransaction)
    if account_id is not None:
        base = base.where(
            (CashTransaction.account_id == account_id)
            | (CashTransaction.to_account_id == account_id)
        )
    if transaction_type:
        base = base.where(CashTransaction.transaction_type == transaction_type.value)
    if category_id is not None:
        base = base.where(CashTransaction.category_id == category_id)
    if date_from:
        base = base.where(CashTransaction.transaction_date >= date_from)
    if date_to:
        base = base.where(CashTransaction.transaction_date <= date_to)

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    rows = (
        await db.execute(
            base.order_by(CashTransaction.transaction_date.desc(), CashTransaction.id.desc())
            .offset(skip).limit(limit)
        )
    ).scalars().all()
    items = [await _serialize_transaction(db, t, claims) for t in rows]
    return {"total": total, "items": items}


@router.get(
    "/transactions/{transaction_id}",
    response_model=CashTransactionResponse,
    responses={**_auth, **_404},
    tags=["Касса — операции"],
)
async def get_transaction_ep(
    transaction_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    t = await db.get(CashTransaction, (claims.tenant_id, transaction_id))
    if t is None:
        raise NotFoundException("Операция не найдена")
    return await _serialize_transaction(db, t, claims)


async def _validate_for_create(
    db: AsyncSession, body: CashTransactionCreate, claims: TenantClaims
) -> tuple[Account, TransactionCategory, Account | None]:
    account = await db.get(Account, (claims.tenant_id, body.account_id))
    if account is None:
        raise NotFoundException("Счёт не найден")
    if not account.is_active:
        raise BadRequestException("Счёт неактивен")

    category = await db.get(TransactionCategory, (claims.tenant_id, body.category_id))
    if category is None:
        raise NotFoundException("Категория не найдена")

    to_account = None
    if body.transaction_type == CashflowTransactionType.TRANSFER:
        if body.to_account_id is None:
            raise BadRequestException("Для перевода обязателен to_account_id")
        if body.to_account_id == body.account_id:
            raise BadRequestException("Счёт-источник и счёт-получатель совпадают")
        to_account = await db.get(Account, (claims.tenant_id, body.to_account_id))
        if to_account is None:
            raise NotFoundException("Счёт назначения не найден")
        if not to_account.is_active:
            raise BadRequestException("Счёт назначения неактивен")
        if category.transaction_type != CashflowTransactionType.TRANSFER.value:
            raise BadRequestException("Для перевода нужна категория типа transfer")
    else:
        if category.transaction_type != body.transaction_type.value:
            raise BadRequestException(
                "Тип категории не совпадает с типом операции"
            )
        if body.to_account_id is not None:
            raise BadRequestException("to_account_id используется только для переводов")
    return account, category, to_account


@router.post(
    "/transactions",
    response_model=CashTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**_auth, **_400, **_404},
    tags=["Касса — операции"],
)
async def create_transaction_ep(
    body: CashTransactionCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    await _validate_for_create(db, body, claims)
    t = CashTransaction(
        tenant_id=claims.tenant_id,
        transaction_type=body.transaction_type.value,
        account_id=body.account_id,
        to_account_id=body.to_account_id,
        category_id=body.category_id,
        amount=body.amount,
        description=body.description,
        transaction_date=body.transaction_date or datetime.now(),
        order_id=body.order_id,
        salary_id=body.salary_id,
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return await _serialize_transaction(db, t, claims)


@router.patch(
    "/transactions/{transaction_id}",
    response_model=CashTransactionResponse,
    responses={**_auth, **_404, **_400},
    tags=["Касса — операции"],
)
async def update_transaction_ep(
    transaction_id: int,
    body: CashTransactionUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    t = await db.get(CashTransaction, (claims.tenant_id, transaction_id))
    if t is None:
        raise NotFoundException("Операция не найдена")
    data = body.model_dump(exclude_unset=True)
    if "category_id" in data:
        cat = await db.get(TransactionCategory, (claims.tenant_id, data["category_id"]))
        if cat is None:
            raise NotFoundException("Категория не найдена")
        if cat.transaction_type != t.transaction_type:
            raise BadRequestException(
                "Категория должна быть того же типа, что и операция"
            )
    for k, v in data.items():
        setattr(t, k, v)
    await db.flush()
    await db.refresh(t)
    return await _serialize_transaction(db, t, claims)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_auth, **_404},
    tags=["Касса — операции"],
)
async def delete_transaction_ep(
    transaction_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
) -> Response:
    t = await db.get(CashTransaction, (claims.tenant_id, transaction_id))
    if t is None:
        raise NotFoundException("Операция не найдена")
    await db.delete(t)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
@router.get(
    "/summary",
    response_model=CashflowSummary,
    responses=_auth,
    tags=["Касса — сводка"],
)
async def cashflow_summary(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(require_accountant_or_admin),
):
    accounts = (
        await db.execute(
            select(Account).where(Account.is_active.is_(True)).order_by(Account.id)
        )
    ).scalars().all()
    serialized_accounts = [await _serialize_account(db, a) for a in accounts]
    total_balance = sum(
        (Decimal(a["current_balance"]) for a in serialized_accounts), Decimal(0)
    )

    where_clauses = []
    params = {}
    if date_from is not None:
        where_clauses.append("transaction_date >= :df")
        params["df"] = date_from
    if date_to is not None:
        where_clauses.append("transaction_date <= :dt")
        params["dt"] = date_to
    where_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

    income = (await db.execute(text(
        f"SELECT COALESCE(SUM(amount), 0) FROM app.cash_transactions "
        f"WHERE transaction_type='income'{where_sql}"
    ), params)).scalar() or Decimal(0)
    expense = (await db.execute(text(
        f"SELECT COALESCE(SUM(amount), 0) FROM app.cash_transactions "
        f"WHERE transaction_type='expense'{where_sql}"
    ), params)).scalar() or Decimal(0)

    return {
        "total_balance": total_balance,
        "total_income": Decimal(income),
        "total_expense": Decimal(expense),
        "net_flow": Decimal(income) - Decimal(expense),
        "accounts": serialized_accounts,
    }
