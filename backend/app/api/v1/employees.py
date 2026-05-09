"""Сотрудники — async CRUD + опциональное создание учётной записи User."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_admin
from app.core.security import TenantClaims, get_password_hash
from app.dependencies import get_current_claims, get_tenant_db
from app.models.employee import Employee, EmployeePosition
from app.models.user import User, UserRole
from app.schemas.employee import (
    Employee as EmployeeSchema,
    EmployeeCreate,
    EmployeeUpdate,
)
from app.schemas.responses import ErrorResponse, LabelValueItem

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Сотрудник не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_admin = {**_auth, 403: {"model": ErrorResponse, "description": "Только для администратора"}}


_POSITION_LABELS = {
    EmployeePosition.ADMIN.value: "Администратор",
    EmployeePosition.MANAGER.value: "Менеджер",
    EmployeePosition.MECHANIC.value: "Механик",
}
_ROLE_LABELS = {
    UserRole.ADMIN.value: "Администратор",
    UserRole.MANAGER.value: "Менеджер",
    UserRole.MECHANIC.value: "Механик",
    UserRole.ACCOUNTANT.value: "Бухгалтер",
}


@router.get("/positions", response_model=list[LabelValueItem])
def list_positions() -> list[LabelValueItem]:
    return [LabelValueItem(value=p.value, label=_POSITION_LABELS[p.value]) for p in EmployeePosition]


@router.get("/user-roles", response_model=list[LabelValueItem])
def list_user_roles() -> list[LabelValueItem]:
    return [LabelValueItem(value=r.value, label=_ROLE_LABELS[r.value]) for r in UserRole]


@router.get("/", response_model=list[EmployeeSchema], responses=_auth)
async def list_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    result = await db.execute(
        select(Employee).order_by(Employee.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get(
    "/{employee_id}",
    response_model=EmployeeSchema,
    responses={**_auth, **_404},
)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    e = await db.get(Employee, (claims.tenant_id, employee_id))
    if e is None:
        raise NotFoundException("Сотрудник не найден")
    return e


@router.post(
    "/",
    response_model=EmployeeSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_admin, 400: {"model": ErrorResponse, "description": "Дубликат логина или email"}},
)
async def create_employee(
    body: EmployeeCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    employee_data = body.model_dump(exclude={"username", "password", "user_role"})
    if hasattr(employee_data.get("position"), "value"):
        employee_data["position"] = employee_data["position"].value
    employee = Employee(tenant_id=claims.tenant_id, **employee_data)
    db.add(employee)
    await db.flush()  # получаем employee.id

    # Создание связанной учётки.
    if body.username and body.password and body.user_role:
        email_for_user = body.email or f"{body.username}@autoservice.local"
        existing = await db.execute(
            select(User).where(
                or_(User.username == body.username, User.email == email_for_user)
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином или email уже существует",
            )
        db.add(User(
            tenant_id=claims.tenant_id,
            username=body.username,
            email=email_for_user,
            password_hash=get_password_hash(body.password),
            role=body.user_role.value if hasattr(body.user_role, "value") else body.user_role,
            employee_id=employee.id,
            is_active=True,
            password_must_be_changed=False,
        ))
        await db.flush()
    await db.refresh(employee)
    return employee


@router.put(
    "/{employee_id}",
    response_model=EmployeeSchema,
    responses={**_admin, **_404},
)
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    e = await db.get(Employee, (claims.tenant_id, employee_id))
    if e is None:
        raise NotFoundException("Сотрудник не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "position" and hasattr(v, "value"):
            v = v.value
        setattr(e, k, v)
    await db.flush()
    await db.refresh(e)
    return e
