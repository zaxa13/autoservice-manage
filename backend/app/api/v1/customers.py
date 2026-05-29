"""Клиенты — пример эталонного async-роутера для shared-DB архитектуры.

Все запросы автоматом отфильтрованы RLS под `tenant_id` из JWT — не нужно
явных `WHERE tenant_id = ...` фильтров в SELECT и явной проставки `tenant_id`
в INSERT (RLS WITH CHECK + либо явно, либо через `app.current_tenant()`
при server_default).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.customer import Customer
from app.schemas.customer import (
    Customer as CustomerSchema,
    CustomerCreate,
    CustomerUpdate,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Клиент не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}
_conflict = {
    409: {"model": ErrorResponse, "description": "Дубликат по телефону"},
}


def _normalize_phone(phone: str) -> str:
    s = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if s.startswith("+7"):
        return s
    if s.startswith("7"):
        return "+" + s
    if s.startswith("8"):
        return "+7" + s[1:]
    return "+7" + s


async def _find_customer_with_same_phone(
    db: AsyncSession,
    phone: str,
    *,
    exclude_id: int | None = None,
) -> Customer | None:
    """Найти клиента с эквивалентным номером телефона.

    Сравнение идёт по всем правдоподобным форматам хранения: каноничный
    `+7XXXXXXXXXX`, легаси `8XXXXXXXXXX`, `7XXXXXXXXXX`, голые 10 цифр.
    Тенант-фильтр RLS включён выше по стеку — здесь явный WHERE не нужен.
    """
    normalized = _normalize_phone(phone)
    if len(normalized) < 12:
        return None
    national = normalized[2:]
    if len(national) != 10 or not national.isdigit():
        return None
    candidates = {normalized, "8" + national, "7" + national, national}
    stmt = select(Customer).where(Customer.phone.in_(candidates))
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none()


def _duplicate_phone_error(existing: Customer) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "duplicate_phone",
            "message": "Клиент с таким телефоном уже существует",
            "existing_customer_id": existing.id,
            "existing_customer_name": existing.full_name,
        },
    )


@router.get(
    "/",
    response_model=list[CustomerSchema],
    summary="Список клиентов",
    responses=_auth,
)
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> list[CustomerSchema]:
    result = await db.execute(
        select(Customer).order_by(Customer.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get(
    "/search/by-phone",
    response_model=list[CustomerSchema],
    summary="Поиск клиентов по телефону",
    responses=_auth,
)
async def search_by_phone(
    phone: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> list[CustomerSchema]:
    normalized = _normalize_phone(phone)
    raw = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    result = await db.execute(
        select(Customer).where(
            or_(Customer.phone.like(f"%{normalized}%"), Customer.phone.like(f"%{raw}%"))
        )
    )
    return list(result.scalars().all())


@router.get(
    "/{customer_id}",
    response_model=CustomerSchema,
    summary="Клиент по ID",
    responses={**_auth, **_404},
)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
) -> CustomerSchema:
    customer = await db.get(Customer, (_claims.tenant_id, customer_id))
    if customer is None:
        raise NotFoundException("Клиент не найден")
    return customer


@router.post(
    "/",
    response_model=CustomerSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать клиента",
    responses={**_write, **_conflict},
)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> CustomerSchema:
    existing = await _find_customer_with_same_phone(db, body.phone)
    if existing is not None:
        raise _duplicate_phone_error(existing)
    customer = Customer(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.put(
    "/{customer_id}",
    response_model=CustomerSchema,
    summary="Обновить клиента",
    responses={**_write, **_404, **_conflict},
)
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> CustomerSchema:
    customer = await db.get(Customer, (claims.tenant_id, customer_id))
    if customer is None:
        raise NotFoundException("Клиент не найден")
    patch = body.model_dump(exclude_unset=True)
    if "phone" in patch and patch["phone"]:
        existing = await _find_customer_with_same_phone(
            db, patch["phone"], exclude_id=customer_id
        )
        if existing is not None:
            raise _duplicate_phone_error(existing)
    for k, v in patch.items():
        setattr(customer, k, v)
    await db.flush()
    await db.refresh(customer)
    return customer
