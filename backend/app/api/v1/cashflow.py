from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.cashflow import TransactionType
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
from app.services.cashflow_service import (
    create_account,
    create_category,
    create_transaction,
    delete_account,
    delete_category,
    delete_transaction,
    get_account,
    get_accounts,
    get_cashflow_summary,
    get_categories,
    get_transaction,
    get_transactions,
    update_account,
    update_transaction,
)
from app.core.permissions import require_accountant_or_admin, require_admin

router = APIRouter()

_auth = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Только бухгалтер / администратор"},
}
_404 = {404: {"model": ErrorResponse, "description": "Объект не найден"}}
_400 = {400: {"model": ErrorResponse, "description": "Некорректные данные"}}


# ── Accounts ──────────────────────────────────────────────────────────────────

@router.get(
    "/accounts",
    response_model=List[AccountResponse],
    status_code=status.HTTP_200_OK,
    summary="Список счетов",
    description=(
        "Возвращает все активные счета (касса, банки) с текущим остатком. "
        "Остаток = начальный баланс ± все проведённые операции."
    ),
    responses=_auth,
    tags=["Касса — счета"],
)
def list_accounts(
    include_inactive: bool = Query(False, description="Включить неактивные счета"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> List[AccountResponse]:
    return get_accounts(db, include_inactive=include_inactive)


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать счёт",
    description=(
        "Создание нового счёта / регистра денежных средств. "
        "Поле `initial_balance` задаёт начальный остаток при переходе с другой системы учёта. "
        "Только администратор."
    ),
    responses={**_auth, **_400},
    tags=["Касса — счета"],
)
def create_new_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AccountResponse:
    return create_account(db, data)


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить счёт",
    description="Детальная информация по счёту с текущим остатком.",
    responses={**_auth, **_404},
    tags=["Касса — счета"],
)
def get_single_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> AccountResponse:
    return get_account(db, account_id)


@router.patch(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить счёт",
    description="Изменить название или активность счёта. Только администратор.",
    responses={**_auth, **_404},
    tags=["Касса — счета"],
)
def update_existing_account(
    account_id: int,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AccountResponse:
    return update_account(db, account_id, data)


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить счёт",
    description=(
        "Удаление счёта без истории операций. "
        "Если по счёту есть транзакции — удаление запрещено, используйте деактивацию через PATCH. "
        "Только администратор."
    ),
    responses={**_auth, **_404, **_400},
    tags=["Касса — счета"],
)
def delete_existing_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    delete_account(db, account_id)


# ── Categories ────────────────────────────────────────────────────────────────

@router.get(
    "/categories",
    response_model=List[TransactionCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Список категорий операций",
    description=(
        "Возвращает все активные категории. Системные категории помечены флагом `is_system=true` "
        "и не могут быть удалены. Опциональная фильтрация по типу операции."
    ),
    responses=_auth,
    tags=["Касса — категории"],
)
def list_categories(
    transaction_type: Optional[TransactionType] = Query(None, description="Фильтр по типу: income, expense, transfer"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> List[TransactionCategoryResponse]:
    return get_categories(db, transaction_type=transaction_type)


@router.post(
    "/categories",
    response_model=TransactionCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать категорию",
    description="Создание пользовательской категории операции.",
    responses={**_auth, **_400},
    tags=["Касса — категории"],
)
def create_new_category(
    data: TransactionCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> TransactionCategoryResponse:
    return create_category(db, data)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
    description=(
        "Удаление пользовательской категории. "
        "Системные категории и категории с привязанными операциями удалить нельзя."
    ),
    responses={**_auth, **_404, **_400},
    tags=["Касса — категории"],
)
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    delete_category(db, category_id)


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get(
    "/transactions",
    response_model=CashflowListResponse,
    status_code=status.HTTP_200_OK,
    summary="Список операций",
    description=(
        "Возвращает операции движения денежных средств с фильтрацией и пагинацией. "
        "Фильтры: счёт, тип операции, категория, диапазон дат."
    ),
    responses=_auth,
    tags=["Касса — операции"],
)
def list_transactions(
    account_id: Optional[int] = Query(None, description="Фильтр по счёту"),
    transaction_type: Optional[TransactionType] = Query(None, description="Тип: income, expense, transfer"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    date_from: Optional[datetime] = Query(None, description="Дата начала (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Дата конца (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(50, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> CashflowListResponse:
    total, items = get_transactions(
        db,
        account_id=account_id,
        transaction_type=transaction_type,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return CashflowListResponse(total=total, items=items)


@router.get(
    "/transactions/{transaction_id}",
    response_model=CashTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить операцию",
    description="Детальная информация по одной операции.",
    responses={**_auth, **_404},
    tags=["Касса — операции"],
)
def get_single_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> CashTransactionResponse:
    return get_transaction(db, transaction_id)


@router.post(
    "/transactions",
    response_model=CashTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать операцию",
    description=(
        "Создание ручной операции: приход, расход или перевод между счетами.\n\n"
        "**Приход** (`income`): деньги поступают на `account_id`.\n\n"
        "**Расход** (`expense`): деньги списываются со `account_id`.\n\n"
        "**Перевод** (`transfer`): деньги уходят со `account_id` и поступают на `to_account_id`. "
        "Категория должна быть типа `transfer`.\n\n"
        "Возвращает 400 при несовпадении типа категории с типом операции, "
        "отсутствии `to_account_id` для перевода или неактивном счёте."
    ),
    responses={**_auth, **_400, **_404},
    tags=["Касса — операции"],
)
def create_new_transaction(
    data: CashTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> CashTransactionResponse:
    return create_transaction(db, data)


@router.patch(
    "/transactions/{transaction_id}",
    response_model=CashTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить операцию",
    description=(
        "Изменить сумму, описание, дату или категорию операции. "
        "Тип операции, счёт и привязки к заказу/зарплате не меняются. "
        "Только администратор."
    ),
    responses={**_auth, **_404, **_400},
    tags=["Касса — операции"],
)
def update_existing_transaction(
    transaction_id: int,
    data: CashTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CashTransactionResponse:
    return update_transaction(db, transaction_id, data)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить операцию",
    description="Удаление операции. Только администратор.",
    responses={**_auth, **_404},
    tags=["Касса — операции"],
)
def remove_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    delete_transaction(db, transaction_id)


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=CashflowSummary,
    status_code=status.HTTP_200_OK,
    summary="Сводка по кассе",
    description=(
        "Возвращает суммарный остаток по всем счетам, общий приход и расход за период, "
        "а также остаток по каждому счёту отдельно. "
        "Если период не указан — учитываются все операции."
    ),
    responses=_auth,
    tags=["Касса — сводка"],
)
def cashflow_summary(
    date_from: Optional[datetime] = Query(None, description="Начало периода (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Конец периода (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
) -> CashflowSummary:
    return get_cashflow_summary(db, date_from=date_from, date_to=date_to)
