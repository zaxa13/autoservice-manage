from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.cashflow import Account, AccountType, CashTransaction, TransactionCategory, TransactionType
from app.schemas.cashflow import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    CashTransactionCreate,
    CashTransactionUpdate,
    TransactionCategoryCreate,
)
from app.core.exceptions import BadRequestException, NotFoundException


# ── System category names ─────────────────────────────────────────────────────

SYSTEM_CATEGORY_ORDER_PAYMENT = "Оплата заказа"
SYSTEM_CATEGORY_ORDER_PAYMENT_REVERSAL = "Отмена оплаты заказа"
SYSTEM_CATEGORY_SALARY = "Выплата зарплаты"
SYSTEM_CATEGORY_INITIAL_BALANCE = "Начальный остаток"
SYSTEM_CATEGORY_TRANSFER = "Перевод между счетами"


def seed_system_categories(db: Session) -> None:
    """Создать системные категории если их нет (вызывается при старте)."""
    system_cats = [
        (SYSTEM_CATEGORY_ORDER_PAYMENT, TransactionType.INCOME),
        (SYSTEM_CATEGORY_ORDER_PAYMENT_REVERSAL, TransactionType.EXPENSE),
        (SYSTEM_CATEGORY_SALARY, TransactionType.EXPENSE),
        (SYSTEM_CATEGORY_INITIAL_BALANCE, TransactionType.INCOME),
        (SYSTEM_CATEGORY_TRANSFER, TransactionType.TRANSFER),
    ]
    for name, tx_type in system_cats:
        exists = (
            db.query(TransactionCategory)
            .filter(TransactionCategory.name == name, TransactionCategory.is_system == True)
            .first()
        )
        if not exists:
            db.add(TransactionCategory(name=name, transaction_type=tx_type, is_system=True))
    db.commit()


# ── Balance helpers ───────────────────────────────────────────────────────────

def _calc_account_balance(db: Session, account: Account) -> Decimal:
    """Рассчитать текущий остаток счёта."""
    income = (
        db.query(func.sum(CashTransaction.amount))
        .filter(
            CashTransaction.account_id == account.id,
            CashTransaction.transaction_type == TransactionType.INCOME,
        )
        .scalar()
        or Decimal("0")
    )
    expense = (
        db.query(func.sum(CashTransaction.amount))
        .filter(
            CashTransaction.account_id == account.id,
            CashTransaction.transaction_type == TransactionType.EXPENSE,
        )
        .scalar()
        or Decimal("0")
    )
    # Переводы: деньги уходят со счёта-источника
    transfer_out = (
        db.query(func.sum(CashTransaction.amount))
        .filter(
            CashTransaction.account_id == account.id,
            CashTransaction.transaction_type == TransactionType.TRANSFER,
        )
        .scalar()
        or Decimal("0")
    )
    # Переводы: деньги приходят на счёт-назначение
    transfer_in = (
        db.query(func.sum(CashTransaction.amount))
        .filter(
            CashTransaction.to_account_id == account.id,
            CashTransaction.transaction_type == TransactionType.TRANSFER,
        )
        .scalar()
        or Decimal("0")
    )
    return account.initial_balance + income - expense - transfer_out + transfer_in


def _to_account_response(db: Session, account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        initial_balance=account.initial_balance,
        current_balance=_calc_account_balance(db, account),
        is_active=account.is_active,
        created_at=account.created_at,
    )


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_accounts(db: Session, include_inactive: bool = False) -> List[AccountResponse]:
    query = db.query(Account)
    if not include_inactive:
        query = query.filter(Account.is_active == True)
    accounts = query.order_by(Account.id.asc()).all()
    return [_to_account_response(db, a) for a in accounts]


def get_account(db: Session, account_id: int) -> AccountResponse:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise NotFoundException("Счёт не найден")
    return _to_account_response(db, account)


def create_account(db: Session, data: AccountCreate) -> AccountResponse:
    account = Account(
        name=data.name,
        account_type=data.account_type,
        initial_balance=data.initial_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_account_response(db, account)


def update_account(db: Session, account_id: int, data: AccountUpdate) -> AccountResponse:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise NotFoundException("Счёт не найден")
    if data.name is not None:
        account.name = data.name
    if data.is_active is not None:
        account.is_active = data.is_active
    db.commit()
    db.refresh(account)
    return _to_account_response(db, account)


# ── Transaction Categories ────────────────────────────────────────────────────

def delete_account(db: Session, account_id: int) -> None:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise NotFoundException("Счёт не найден")
    has_transactions = (
        db.query(CashTransaction)
        .filter(
            (CashTransaction.account_id == account_id) |
            (CashTransaction.to_account_id == account_id)
        )
        .first()
    )
    if has_transactions:
        raise BadRequestException(
            "Нельзя удалить счёт с историей операций. Деактивируйте его через редактирование."
        )
    db.delete(account)
    db.commit()


def get_categories(
    db: Session,
    transaction_type: Optional[TransactionType] = None,
) -> List[TransactionCategory]:
    query = db.query(TransactionCategory).filter(TransactionCategory.is_active == True)
    if transaction_type:
        query = query.filter(TransactionCategory.transaction_type == transaction_type)
    return query.order_by(TransactionCategory.is_system.desc(), TransactionCategory.name.asc()).all()


def create_category(db: Session, data: TransactionCategoryCreate) -> TransactionCategory:
    category = TransactionCategory(
        name=data.name,
        transaction_type=data.transaction_type,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = db.query(TransactionCategory).filter(TransactionCategory.id == category_id).first()
    if not category:
        raise NotFoundException("Категория не найдена")
    if category.is_system:
        raise BadRequestException("Системные категории нельзя удалять")
    has_transactions = (
        db.query(CashTransaction).filter(CashTransaction.category_id == category_id).first()
    )
    if has_transactions:
        raise BadRequestException("Нельзя удалить категорию, к которой привязаны операции")
    db.delete(category)
    db.commit()


# ── Transactions ──────────────────────────────────────────────────────────────

def _get_transaction_or_404(db: Session, transaction_id: int) -> CashTransaction:
    tx = (
        db.query(CashTransaction)
        .options(
            joinedload(CashTransaction.account),
            joinedload(CashTransaction.to_account),
            joinedload(CashTransaction.category),
        )
        .filter(CashTransaction.id == transaction_id)
        .first()
    )
    if not tx:
        raise NotFoundException("Операция не найдена")
    return tx


def get_transactions(
    db: Session,
    account_id: Optional[int] = None,
    transaction_type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[int, List[CashTransaction]]:
    query = db.query(CashTransaction).options(
        joinedload(CashTransaction.account),
        joinedload(CashTransaction.to_account),
        joinedload(CashTransaction.category),
    )
    if account_id:
        query = query.filter(
            (CashTransaction.account_id == account_id)
            | (CashTransaction.to_account_id == account_id)
        )
    if transaction_type:
        query = query.filter(CashTransaction.transaction_type == transaction_type)
    if category_id:
        query = query.filter(CashTransaction.category_id == category_id)
    if date_from:
        query = query.filter(CashTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(CashTransaction.transaction_date <= date_to)

    total = query.count()
    items = query.order_by(CashTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return total, items


def get_transaction(db: Session, transaction_id: int) -> CashTransaction:
    return _get_transaction_or_404(db, transaction_id)


def create_transaction(db: Session, data: CashTransactionCreate) -> CashTransaction:
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise NotFoundException("Счёт не найден")
    if not account.is_active:
        raise BadRequestException("Счёт неактивен")

    category = db.query(TransactionCategory).filter(TransactionCategory.id == data.category_id).first()
    if not category:
        raise NotFoundException("Категория не найдена")
    if not category.is_active:
        raise BadRequestException("Категория неактивна")

    if data.transaction_type == TransactionType.TRANSFER:
        if not data.to_account_id:
            raise BadRequestException("Для перевода необходимо указать счёт назначения (to_account_id)")
        if data.to_account_id == data.account_id:
            raise BadRequestException("Счёт источника и счёт назначения не могут совпадать")
        to_account = db.query(Account).filter(Account.id == data.to_account_id).first()
        if not to_account:
            raise NotFoundException("Счёт назначения не найден")
        if not to_account.is_active:
            raise BadRequestException("Счёт назначения неактивен")
        if category.transaction_type != TransactionType.TRANSFER:
            raise BadRequestException("Для перевода выберите категорию типа 'transfer'")
    else:
        if data.to_account_id:
            raise BadRequestException("Поле to_account_id используется только для переводов")
        if category.transaction_type != data.transaction_type:
            raise BadRequestException(
                f"Категория относится к типу '{category.transaction_type.value}', "
                f"а операция — '{data.transaction_type.value}'"
            )

    tx_date = data.transaction_date or datetime.utcnow()

    tx = CashTransaction(
        transaction_type=data.transaction_type,
        account_id=data.account_id,
        to_account_id=data.to_account_id,
        category_id=data.category_id,
        amount=data.amount,
        description=data.description,
        transaction_date=tx_date,
        order_id=data.order_id,
        salary_id=data.salary_id,
    )
    db.add(tx)
    db.commit()
    return _get_transaction_or_404(db, tx.id)


def update_transaction(db: Session, transaction_id: int, data: CashTransactionUpdate) -> CashTransaction:
    tx = db.query(CashTransaction).filter(CashTransaction.id == transaction_id).first()
    if not tx:
        raise NotFoundException("Операция не найдена")
    if data.amount is not None:
        tx.amount = data.amount
    if data.description is not None:
        tx.description = data.description
    if data.transaction_date is not None:
        tx.transaction_date = data.transaction_date
    if data.category_id is not None:
        category = db.query(TransactionCategory).filter(TransactionCategory.id == data.category_id).first()
        if not category:
            raise NotFoundException("Категория не найдена")
        if category.transaction_type != tx.transaction_type:
            raise BadRequestException(
                f"Категория типа '{category.transaction_type.value}' не подходит для операции типа '{tx.transaction_type.value}'"
            )
        tx.category_id = data.category_id
    db.commit()
    return _get_transaction_or_404(db, tx.id)


def delete_transaction(db: Session, transaction_id: int) -> None:
    tx = db.query(CashTransaction).filter(CashTransaction.id == transaction_id).first()
    if not tx:
        raise NotFoundException("Операция не найдена")
    db.delete(tx)
    db.commit()


# ── Summary ───────────────────────────────────────────────────────────────────

def get_cashflow_summary(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    accounts = db.query(Account).filter(Account.is_active == True).all()
    account_responses = [_to_account_response(db, a) for a in accounts]
    total_balance = sum(a.current_balance for a in account_responses)

    income_q = db.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == TransactionType.INCOME
    )
    expense_q = db.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == TransactionType.EXPENSE
    )
    if date_from:
        income_q = income_q.filter(CashTransaction.transaction_date >= date_from)
        expense_q = expense_q.filter(CashTransaction.transaction_date >= date_from)
    if date_to:
        income_q = income_q.filter(CashTransaction.transaction_date <= date_to)
        expense_q = expense_q.filter(CashTransaction.transaction_date <= date_to)

    total_income = income_q.scalar() or Decimal("0")
    total_expense = expense_q.scalar() or Decimal("0")

    return {
        "total_balance": total_balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_flow": total_income - total_expense,
        "accounts": account_responses,
    }


# ── Auto-transaction helpers (called from payment_service / salary_service) ───

def _get_or_create_system_category(db: Session, name: str, tx_type: TransactionType) -> TransactionCategory:
    cat = (
        db.query(TransactionCategory)
        .filter(TransactionCategory.name == name, TransactionCategory.is_system == True)
        .first()
    )
    if not cat:
        cat = TransactionCategory(name=name, transaction_type=tx_type, is_system=True)
        db.add(cat)
        db.flush()
    return cat


def _get_default_cash_account(db: Session) -> Optional[Account]:
    """Вернуть первый активный счёт типа cash, если он есть."""
    return (
        db.query(Account)
        .filter(Account.is_active == True, Account.account_type == AccountType.CASH)
        .order_by(Account.id.asc())
        .first()
    )


def _get_default_bank_account(db: Session) -> Optional[Account]:
    """Вернуть первый активный счёт типа bank, если он есть."""
    return (
        db.query(Account)
        .filter(Account.is_active == True, Account.account_type == AccountType.BANK)
        .order_by(Account.id.asc())
        .first()
    )


def record_order_payment(
    db: Session,
    order_id: int,
    amount: Decimal,
    account_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    payment_id: Optional[int] = None,
) -> Optional[CashTransaction]:
    """Автоматически создать приходную операцию при оплате заказа.

    Если account_id не указан — выбирается счёт по методу оплаты:
    cash → первый активный cash-счёт, card/transfer/прочее → первый активный bank-счёт.
    Если подходящего счёта нет — пробуем cash, затем bank. Если счетов нет вообще — пропускаем.
    """
    target_account = None

    if account_id:
        target_account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()

    if not target_account:
        if payment_method == "cash":
            target_account = _get_default_cash_account(db)
        elif payment_method in ("card", "transfer"):
            target_account = _get_default_bank_account(db) or _get_default_cash_account(db)
        else:
            target_account = _get_default_cash_account(db) or _get_default_bank_account(db)

    if not target_account:
        return None

    category = _get_or_create_system_category(db, SYSTEM_CATEGORY_ORDER_PAYMENT, TransactionType.INCOME)

    from app.models.order import Order
    order = db.query(Order).filter(Order.id == order_id).first()
    order_label = order.number if order else f"#{order_id}"

    tx = CashTransaction(
        transaction_type=TransactionType.INCOME,
        account_id=target_account.id,
        category_id=category.id,
        amount=amount,
        description=f"Оплата по заказ-наряду {order_label}",
        order_id=order_id,
        payment_id=payment_id,
    )
    db.add(tx)
    return tx


def _get_order_label(db: Session, order_id: int) -> str:
    from app.models.order import Order
    order = db.query(Order).filter(Order.id == order_id).first()
    return order.number if order else f"#{order_id}"


def _get_account_for_method(db: Session, payment_method: Optional[str]) -> Optional[Account]:
    if payment_method == "cash":
        return _get_default_cash_account(db)
    elif payment_method in ("card", "transfer"):
        return _get_default_bank_account(db) or _get_default_cash_account(db)
    return _get_default_cash_account(db) or _get_default_bank_account(db)


def _get_income_tx_by_payment(db: Session, payment_id: int) -> Optional[CashTransaction]:
    """Приходная транзакция привязанная к конкретному payment_id."""
    return (
        db.query(CashTransaction)
        .filter(
            CashTransaction.payment_id == payment_id,
            CashTransaction.transaction_type == TransactionType.INCOME,
        )
        .first()
    )


def reverse_order_cashflow_transaction(
    db: Session,
    order_id: int,
    reversal_amount: Optional[Decimal] = None,
    payment_id: Optional[int] = None,
    match_amount: Optional[Decimal] = None,
) -> Optional[CashTransaction]:
    """Создать сторнирующую расходную транзакцию для отмены оплаты заказа.

    Поиск исходной транзакции:
    1. По payment_id — точное совпадение (новые записи)
    2. Fallback по order_id + сумме — для записей без payment_id (созданных до миграции)
    3. Fallback по order_id — последняя приходная (cancel_all без payment_id)
    """
    original = None

    if payment_id:
        original = _get_income_tx_by_payment(db, payment_id)

    # Fallback для старых записей без payment_id
    if not original and match_amount is not None:
        original = (
            db.query(CashTransaction)
            .filter(
                CashTransaction.order_id == order_id,
                CashTransaction.transaction_type == TransactionType.INCOME,
                CashTransaction.amount == match_amount,
                CashTransaction.payment_id.is_(None),
            )
            .order_by(CashTransaction.id.desc())
            .first()
        )

    # Финальный fallback — последняя приходная по заказу
    if not original:
        original = (
            db.query(CashTransaction)
            .filter(
                CashTransaction.order_id == order_id,
                CashTransaction.transaction_type == TransactionType.INCOME,
            )
            .order_by(CashTransaction.id.desc())
            .first()
        )

    if not original:
        return None

    amount = reversal_amount if reversal_amount is not None else original.amount
    order_label = _get_order_label(db, order_id)
    category = _get_or_create_system_category(
        db, SYSTEM_CATEGORY_ORDER_PAYMENT_REVERSAL, TransactionType.EXPENSE
    )

    tx = CashTransaction(
        transaction_type=TransactionType.EXPENSE,
        account_id=original.account_id,
        category_id=category.id,
        amount=amount,
        description=f"Отмена оплаты по заказ-наряду {order_label}",
        order_id=order_id,
        payment_id=payment_id,
    )
    db.add(tx)
    return tx


def adjust_order_cashflow_transaction(
    db: Session,
    order_id: int,
    new_amount: Decimal,
    new_payment_method: Optional[str] = None,
    payment_id: Optional[int] = None,
) -> None:
    """Скорректировать кассу при редактировании платежа через сторнирование.

    Сторнируем исходную транзакцию и создаём новую с актуальными данными.
    Вся история остаётся.
    """
    original = _get_last_income_tx(db, order_id)

    if original:
        # Сторнируем исходную запись
        order_label = _get_order_label(db, order_id)
        reversal_category = _get_or_create_system_category(
            db, SYSTEM_CATEGORY_ORDER_PAYMENT_REVERSAL, TransactionType.EXPENSE
        )
        reversal = CashTransaction(
            transaction_type=TransactionType.EXPENSE,
            account_id=original.account_id,
            category_id=reversal_category.id,
            amount=original.amount,
            description=f"Корректировка оплаты по заказ-наряду {order_label}",
            order_id=order_id,
            payment_id=payment_id,
        )
        db.add(reversal)
        db.flush()

    # Создаём новую транзакцию с актуальными данными
    record_order_payment(
        db,
        order_id=order_id,
        amount=new_amount,
        payment_method=new_payment_method,
        payment_id=payment_id,
    )


def record_salary_payment(
    db: Session,
    salary_id: int,
    amount: Decimal,
    employee_name: str,
    account_id: Optional[int] = None,
) -> Optional[CashTransaction]:
    """Автоматически создать расходную операцию при выплате зарплаты."""
    target_account = None
    if account_id:
        target_account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()
    if not target_account:
        target_account = _get_default_cash_account(db)
    if not target_account:
        return None

    category = _get_or_create_system_category(db, SYSTEM_CATEGORY_SALARY, TransactionType.EXPENSE)

    tx = CashTransaction(
        transaction_type=TransactionType.EXPENSE,
        account_id=target_account.id,
        category_id=category.id,
        amount=amount,
        description=f"Выплата зарплаты: {employee_name}",
        salary_id=salary_id,
    )
    db.add(tx)
    return tx
