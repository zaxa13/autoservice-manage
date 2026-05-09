"""Записи на обслуживание — async CRUD."""
from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin
from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.appointment import Appointment
from app.models.appointment_post import AppointmentPost
from app.models.employee import Employee
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.schemas.appointment import (
    Appointment as AppointmentSchema,
    AppointmentCreate,
    AppointmentUpdate,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Запись не найдена"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


async def _serialize(db: AsyncSession, a: Appointment, claims: TenantClaims) -> dict:
    vehicle_info = None
    if a.vehicle_id:
        v = await db.get(Vehicle, (claims.tenant_id, a.vehicle_id))
        if v is not None:
            brand = await db.get(VehicleBrand, (claims.tenant_id, v.brand_id))
            model = await db.get(VehicleModel, (claims.tenant_id, v.model_id))
            vehicle_info = {
                "id": v.id,
                "license_plate": v.license_plate,
                "year": v.year,
                "brand": {"id": brand.id, "name": brand.name} if brand else None,
                "model": {"id": model.id, "name": model.name} if model else None,
            }
    order_ref = None
    if a.order_id:
        o = await db.get(Order, (claims.tenant_id, a.order_id))
        if o is not None:
            order_ref = {"id": o.id, "number": o.number}
    return {
        "id": a.id, "date": a.date, "time": a.time,
        "customer_name": a.customer_name, "customer_phone": a.customer_phone,
        "description": a.description, "status": a.status,
        "vehicle_id": a.vehicle_id, "employee_id": a.employee_id,
        "post_id": a.post_id, "order_id": a.order_id,
        "sort_order": a.sort_order or 0,
        "created_at": a.created_at, "updated_at": a.updated_at,
        "vehicle": vehicle_info, "order": order_ref,
    }


async def _validate_refs(db: AsyncSession, claims: TenantClaims, data: dict) -> None:
    """Если в payload есть FK-id — проверяем существование (более понятный 404)."""
    if data.get("vehicle_id") is not None:
        if await db.get(Vehicle, (claims.tenant_id, data["vehicle_id"])) is None:
            raise NotFoundException("Транспортное средство не найдено")
    if data.get("employee_id") is not None:
        if await db.get(Employee, (claims.tenant_id, data["employee_id"])) is None:
            raise NotFoundException("Сотрудник не найден")
    if data.get("post_id") is not None:
        if await db.get(AppointmentPost, (claims.tenant_id, data["post_id"])) is None:
            raise NotFoundException("Пост не найден")
    if data.get("order_id") is not None:
        if await db.get(Order, (claims.tenant_id, data["order_id"])) is None:
            raise NotFoundException("Заказ-наряд не найден")


@router.get("/", response_model=list[AppointmentSchema], responses=_auth)
async def list_appointments(
    appointment_date: Optional[date_type] = Query(None, alias="date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    stmt = select(Appointment).order_by(
        Appointment.post_id.asc(),
        Appointment.sort_order.asc(),
        Appointment.time.asc(),
    )
    if appointment_date:
        stmt = stmt.where(Appointment.date == appointment_date)
    stmt = stmt.offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _serialize(db, a, claims) for a in rows]


@router.get(
    "/{appointment_id}",
    response_model=AppointmentSchema,
    responses={**_auth, **_404},
)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    a = await db.get(Appointment, (claims.tenant_id, appointment_id))
    if a is None:
        raise NotFoundException("Запись не найдена")
    return await _serialize(db, a, claims)


@router.post(
    "/",
    response_model=AppointmentSchema,
    status_code=status.HTTP_201_CREATED,
    responses=_write,
)
async def create_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    data = body.model_dump()
    await _validate_refs(db, claims, data)
    if hasattr(data.get("status"), "value"):
        data["status"] = data["status"].value
    if data.get("sort_order") is None:
        data["sort_order"] = 0
    a = Appointment(tenant_id=claims.tenant_id, **data)
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return await _serialize(db, a, claims)


@router.put(
    "/{appointment_id}",
    response_model=AppointmentSchema,
    responses={**_write, **_404},
)
async def update_appointment(
    appointment_id: int,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    a = await db.get(Appointment, (claims.tenant_id, appointment_id))
    if a is None:
        raise NotFoundException("Запись не найдена")
    data = body.model_dump(exclude_unset=True)
    await _validate_refs(db, claims, data)
    if "status" in data and hasattr(data["status"], "value"):
        data["status"] = data["status"].value
    for k, v in data.items():
        setattr(a, k, v)
    await db.flush()
    await db.refresh(a)
    return await _serialize(db, a, claims)


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_write, **_404},
)
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
) -> Response:
    a = await db.get(Appointment, (claims.tenant_id, appointment_id))
    if a is None:
        raise NotFoundException("Запись не найдена")
    await db.delete(a)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
