"""Зарплата — расчёт, ведомости, схема per-employee.

Расчёт:
  base = employee.salary_base
  works_bonus = SUM(order_works.total) WHERE mechanic_id=employee
                AND order.status IN ('paid','completed')
                AND order.completed_at в периоде
                * scheme.works_percentage / 100
  revenue_bonus = SUM(order.total_amount) WHERE order.employee_id=employee
                  (отвественный менеджер) AND status IN ('paid','completed')
                  AND order.created_at в периоде
                  * scheme.revenue_percentage / 100
  total = base + works_bonus + revenue_bonus  (penalty по умолчанию 0)

Pay-операция помимо смены статуса создаёт расходную cashflow-операцию по
категории «Зарплата» (системная, заводится онбордингом). Если категории
нет — pay всё равно работает, но без cashflow-следа.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import require_accountant_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.cashflow import (
    Account,
    CashTransaction,
    CashflowTransactionType,
    TransactionCategory,
)
from app.models.employee import Employee
from app.models.order import Order, OrderWork
from app.models.salary import Salary, SalaryScheme, SalaryStatus
from app.schemas.responses import ErrorResponse
from app.schemas.salary import (
    Salary as SalarySchema,
    SalaryCalculate,
    SalarySchemeResponse,
    SalarySchemeUpdate,
)

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Расчёт не найден"}}
_auth = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Только бухгалтер / администратор"},
}


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------
async def _scheme_for(db: AsyncSession, employee_id: int) -> SalaryScheme | None:
    return (
        await db.execute(select(SalaryScheme).where(SalaryScheme.employee_id == employee_id))
    ).scalar_one_or_none()


async def _calculate(
    db: AsyncSession, body: SalaryCalculate, claims: TenantClaims
) -> Salary:
    if body.period_start > body.period_end:
        raise BadRequestException("period_start не может быть позже period_end")

    employee = await db.get(Employee, (claims.tenant_id, body.employee_id))
    if employee is None:
        raise NotFoundException("Сотрудник не найден")

    scheme = await _scheme_for(db, body.employee_id)
    works_pct = Decimal(str(scheme.works_percentage if scheme else 0))
    revenue_pct = Decimal(str(scheme.revenue_percentage if scheme else 0))

    # Сумма работ механика за период.
    works_total_row = (await db.execute(
        select(OrderWork.total)
        .join(Order, (Order.id == OrderWork.order_id) & (Order.tenant_id == OrderWork.tenant_id))
        .where(
            OrderWork.mechanic_id == body.employee_id,
            Order.status.in_(["paid", "completed"]),
            Order.created_at >= datetime.combine(body.period_start, datetime.min.time()),
            Order.created_at <= datetime.combine(body.period_end, datetime.max.time()),
        )
    )).all()
    works_sum = sum(
        (Decimal(str(row[0] or 0)) for row in works_total_row), Decimal(0)
    )
    works_bonus = (works_sum * works_pct / Decimal(100)).quantize(Decimal("0.01"))

    # Личная выручка ответственного менеджера.
    revenue_rows = (await db.execute(
        select(Order.total_amount)
        .where(
            Order.employee_id == body.employee_id,
            Order.status.in_(["paid", "completed"]),
            Order.created_at >= datetime.combine(body.period_start, datetime.min.time()),
            Order.created_at <= datetime.combine(body.period_end, datetime.max.time()),
        )
    )).all()
    revenue_sum = sum(
        (Decimal(str(row[0] or 0)) for row in revenue_rows), Decimal(0)
    )
    revenue_bonus = (revenue_sum * revenue_pct / Decimal(100)).quantize(Decimal("0.01"))

    base = Decimal(str(employee.salary_base))
    total = (base + works_bonus + revenue_bonus).quantize(Decimal("0.01"))

    salary = Salary(
        tenant_id=claims.tenant_id,
        employee_id=body.employee_id,
        period_start=body.period_start,
        period_end=body.period_end,
        base_salary=base,
        bonus=(works_bonus + revenue_bonus).quantize(Decimal("0.01")),
        penalty=Decimal(0),
        total=total,
        status=SalaryStatus.CALCULATED.value,
    )
    db.add(salary)
    await db.flush()
    await db.refresh(salary)
    return salary


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[SalarySchema], responses=_auth)
async def list_salaries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(require_accountant_or_admin),
):
    rows = (
        await db.execute(
            select(Salary).order_by(Salary.id.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()
    return list(rows)


@router.get("/{salary_id}", response_model=SalarySchema, responses={**_auth, **_404})
async def get_salary(
    salary_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    s = await db.get(Salary, (claims.tenant_id, salary_id))
    if s is None:
        raise NotFoundException("Расчёт не найден")
    return s


@router.post(
    "/calculate",
    response_model=SalarySchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_auth, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def calculate_salary_ep(
    body: SalaryCalculate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    return await _calculate(db, body, claims)


@router.post(
    "/{salary_id}/pay",
    response_model=SalarySchema,
    responses={**_auth, **_404, 400: {"model": ErrorResponse}},
)
async def pay_salary(
    salary_id: int,
    account_id: Optional[int] = Query(None, description="Счёт списания"),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    salary = await db.get(Salary, (claims.tenant_id, salary_id))
    if salary is None:
        raise NotFoundException("Расчёт не найден")
    if salary.status == SalaryStatus.PAID.value:
        raise BadRequestException("Зарплата уже выплачена")

    # Найти счёт (явный или первый активный).
    account: Account | None = None
    if account_id is not None:
        account = await db.get(Account, (claims.tenant_id, account_id))
        if account is None or not account.is_active:
            raise BadRequestException("Счёт не найден или неактивен")
    else:
        account = (
            await db.execute(
                select(Account).where(Account.is_active.is_(True)).order_by(Account.id).limit(1)
            )
        ).scalar_one_or_none()

    salary.status = SalaryStatus.PAID.value
    salary.paid_at = datetime.now(timezone.utc)

    # Cashflow-операция (если есть и счёт, и категория «Зарплата»).
    if account is not None:
        cat = (await db.execute(
            select(TransactionCategory).where(
                TransactionCategory.is_system.is_(True),
                TransactionCategory.name == "Зарплата",
                TransactionCategory.transaction_type == CashflowTransactionType.EXPENSE.value,
            )
        )).scalar_one_or_none()
        if cat is not None:
            employee = await db.get(Employee, (claims.tenant_id, salary.employee_id))
            employee_name = employee.full_name if employee else f"Сотрудник #{salary.employee_id}"
            db.add(CashTransaction(
                tenant_id=claims.tenant_id,
                transaction_type=CashflowTransactionType.EXPENSE.value,
                account_id=account.id,
                to_account_id=None,
                category_id=cat.id,
                amount=salary.total,
                description=f"Выплата зарплаты: {employee_name}",
                transaction_date=datetime.now(timezone.utc),
                salary_id=salary.id,
            ))
    await db.flush()
    await db.refresh(salary)
    return salary


@router.get(
    "/scheme/{employee_id}",
    response_model=SalarySchemeResponse,
    responses={**_auth},
)
async def get_scheme(
    employee_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    if await db.get(Employee, (claims.tenant_id, employee_id)) is None:
        raise NotFoundException("Сотрудник не найден")
    scheme = await _scheme_for(db, employee_id)
    if scheme is None:
        # Виртуальная "пустая" схема, чтобы фронт мог редактировать.
        return {
            "id": None,
            "employee_id": employee_id,
            "works_percentage": Decimal(0),
            "revenue_percentage": Decimal(0),
            "updated_at": None,
        }
    return scheme


@router.put(
    "/scheme/{employee_id}",
    response_model=SalarySchemeResponse,
    responses={**_auth, **_404},
)
async def upsert_scheme(
    employee_id: int,
    body: SalarySchemeUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_accountant_or_admin),
):
    if await db.get(Employee, (claims.tenant_id, employee_id)) is None:
        raise NotFoundException("Сотрудник не найден")
    scheme = await _scheme_for(db, employee_id)
    if scheme is None:
        scheme = SalaryScheme(
            tenant_id=claims.tenant_id,
            employee_id=employee_id,
            works_percentage=body.works_percentage,
            revenue_percentage=body.revenue_percentage,
        )
        db.add(scheme)
    else:
        scheme.works_percentage = body.works_percentage
        scheme.revenue_percentage = body.revenue_percentage
    await db.flush()
    await db.refresh(scheme)
    return scheme
