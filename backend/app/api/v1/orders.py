"""Заказ-наряды — async CRUD на shared-DB.

Wave 3a + 4c:
- list / get / create / update / cancel / complete / delete
- статусы lookup
- mechanic-фильтр через claims.employee_id
- payments (Wave 4c): GET /{id}/payments, POST /{id}/payments —
  ручная оплата (наличные/карта) с авто-созданием cashflow income.

- /print, /print-act — PDF заказ-наряда и акта выполненных работ
  (pdf_service на sync Session → threadpool + sync_tenant_session).

НЕ мигрировано:
- payment cancel/edit (отложено)
- yookassa-эндпоинты (внешняя интеграция)

Номера заказов — через `app.tenant_counters`, атомарный
INSERT...ON CONFLICT DO NOTHING + UPDATE...RETURNING. Формат `ЗН-001`.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_, bindparam, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import require_admin, require_manager_or_admin
from app.core.security import TenantClaims
from app.database import sync_tenant_session
from app.dependencies import get_current_claims, get_tenant_db
from app.services.pdf_service import generate_act_pdf, generate_order_pdf
from app.models.cashflow import (
    Account,
    CashTransaction,
    CashflowTransactionType,
    TransactionCategory,
)
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.order import Order, OrderPart, OrderStatus, OrderWork
from app.models.payment import Payment, PaymentLog, PaymentMethod, PaymentStatus
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.models.warehouse import TransactionType, WarehouseItem, WarehouseTransaction
from app.schemas.payment import Payment as PaymentSchema, PaymentCreate, PaymentLogEntry
from app.schemas.order import (
    Order as OrderSchema,
    OrderCreate,
    OrderDetail,
    OrderListResponse,
    OrderUpdate,
)
from app.schemas.responses import ErrorResponse, LabelValueItem

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Заказ-наряд не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}
_admin = {**_auth, 403: {"model": ErrorResponse, "description": "Только администратор"}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _line_total(price, quantity, discount) -> Decimal:
    """price * quantity * (1 - discount/100)."""
    p = Decimal(str(price))
    q = Decimal(str(quantity))
    d = Decimal(str(discount or 0))
    return (p * q * (Decimal(1) - d / Decimal(100))).quantize(Decimal("0.01"))


async def _next_order_number(db: AsyncSession) -> str:
    """Атомарный per-tenant счётчик: 'ЗН-001', 'ЗН-002', …"""
    await db.execute(
        text(
            "INSERT INTO app.tenant_counters (tenant_id, counter_name, value) "
            "VALUES (app.current_tenant(), 'orders', 0) "
            "ON CONFLICT (tenant_id, counter_name) DO NOTHING"
        )
    )
    result = await db.execute(
        text(
            "UPDATE app.tenant_counters SET value = value + 1 "
            "WHERE tenant_id = app.current_tenant() AND counter_name = 'orders' "
            "RETURNING value"
        )
    )
    n = result.scalar_one()
    return f"ЗН-{n:03d}"


async def _validate_part_refs(db: AsyncSession, items) -> None:
    """Гарантирует, что все part_id из payload реально есть в каталоге тенанта.

    RLS делает фильтрацию по tenant_id автоматически.
    """
    ids = {p.part_id for p in items if p.part_id is not None}
    if not ids:
        return
    stmt = text("SELECT id FROM app.parts WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    found = set((await db.execute(stmt, {"ids": list(ids)})).scalars().all())
    missing = sorted(ids - found)
    if missing:
        raise BadRequestException(
            f"Запчасть из каталога не найдена (id={missing}). "
            "Удалите позицию или выберите другую."
        )


async def _validate_work_refs(db: AsyncSession, items) -> None:
    """Гарантирует, что все work_id из payload реально есть в каталоге тенанта."""
    ids = {w.work_id for w in items if w.work_id is not None}
    if not ids:
        return
    stmt = text("SELECT id FROM app.works WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    found = set((await db.execute(stmt, {"ids": list(ids)})).scalars().all())
    missing = sorted(ids - found)
    if missing:
        raise BadRequestException(
            f"Работа из каталога не найдена (id={missing}). "
            "Удалите позицию или выберите другую."
        )


def _vehicle_dict(v: Vehicle, customer, brand, model) -> dict:
    return {
        "id": v.id,
        "vin": v.vin,
        "license_plate": v.license_plate,
        "brand_id": v.brand_id,
        "model_id": v.model_id,
        "year": v.year,
        "mileage": v.mileage,
        "customer_id": v.customer_id,
        "created_at": v.created_at,
        "customer": customer,
        "brand": ({"id": brand.id, "name": brand.name} if brand else None),
        "model": ({"id": model.id, "name": model.name} if model else None),
    }


async def _serialize_order_works(
    db: AsyncSession, order_id: int, with_refs: bool = True
) -> list[dict]:
    rows = (
        await db.execute(
            select(OrderWork).where(OrderWork.order_id == order_id).order_by(OrderWork.id)
        )
    ).scalars().all()
    if not with_refs or not rows:
        return [
            {
                "id": w.id, "order_id": w.order_id, "work_id": w.work_id,
                "work_name": w.work_name, "mechanic_id": w.mechanic_id,
                "quantity": w.quantity, "price": w.price, "discount": w.discount,
                "total": w.total, "work": None, "mechanic": None,
            }
            for w in rows
        ]
    from app.models.work import Work as WorkModel
    work_ids = {w.work_id for w in rows if w.work_id}
    mech_ids = {w.mechanic_id for w in rows if w.mechanic_id}
    wmap = {}
    mmap = {}
    if work_ids:
        wmap = {
            w.id: w
            for w in (await db.execute(select(WorkModel).where(WorkModel.id.in_(work_ids)))).scalars()
        }
    if mech_ids:
        mmap = {
            e.id: e
            for e in (await db.execute(select(Employee).where(Employee.id.in_(mech_ids)))).scalars()
        }
    return [
        {
            "id": w.id, "order_id": w.order_id, "work_id": w.work_id,
            "work_name": w.work_name, "mechanic_id": w.mechanic_id,
            "quantity": w.quantity, "price": w.price, "discount": w.discount,
            "total": w.total,
            "work": wmap.get(w.work_id),
            "mechanic": mmap.get(w.mechanic_id),
        }
        for w in rows
    ]


async def _serialize_order_parts(
    db: AsyncSession, order_id: int, with_refs: bool = True
) -> list[dict]:
    rows = (
        await db.execute(
            select(OrderPart).where(OrderPart.order_id == order_id).order_by(OrderPart.id)
        )
    ).scalars().all()
    if not with_refs or not rows:
        return [
            {
                "id": p.id, "order_id": p.order_id, "part_id": p.part_id,
                "part_name": p.part_name, "article": p.article,
                "quantity": p.quantity, "price": p.price, "discount": p.discount,
                "total": p.total, "part": None,
            }
            for p in rows
        ]
    from app.models.part import Part as PartModel
    part_ids = {p.part_id for p in rows if p.part_id}
    pmap = {}
    if part_ids:
        # Подтягиваем актуальный остаток из warehouse_items одним запросом,
        # чтобы фронт мог корректно показывать «На складе: N» / «Не хватает»
        # вместо вечного 0 (которое выглядело как «нет на складе»).
        stock_map = dict(
            (await db.execute(
                select(WarehouseItem.part_id, WarehouseItem.quantity)
                .where(WarehouseItem.part_id.in_(part_ids))
            )).all()
        )
        pmap = {
            p.id: {
                "id": p.id, "name": p.name, "part_number": p.part_number,
                "brand": p.brand, "price": p.price,
                "purchase_price_last": p.purchase_price_last,
                "unit": p.unit, "category": p.category,
                "stock_quantity": float(stock_map.get(p.id, 0) or 0),
            }
            for p in (await db.execute(select(PartModel).where(PartModel.id.in_(part_ids)))).scalars()
        }
    return [
        {
            "id": p.id, "order_id": p.order_id, "part_id": p.part_id,
            "part_name": p.part_name, "article": p.article,
            "quantity": p.quantity, "price": p.price, "discount": p.discount,
            "total": p.total,
            "part": pmap.get(p.part_id),
        }
        for p in rows
    ]


async def _serialize_orders_bulk(
    db: AsyncSession, orders: list[Order], claims: TenantClaims
) -> list[dict]:
    """Сериализация списка заказов одним батчем: вместо N×5 точечных SELECT
    делает по одному IN-запросу на связанную таблицу (vehicles, customers,
    brands, models, mechanics). Используется только в list-режиме (detail=False)."""
    if not orders:
        return []

    tenant_id = claims.tenant_id
    vehicle_ids = list({o.vehicle_id for o in orders})
    mechanic_ids = list({o.mechanic_id for o in orders if o.mechanic_id})

    vehicles: dict[int, Vehicle] = {}
    if vehicle_ids:
        rows = (await db.execute(
            select(Vehicle).where(
                Vehicle.tenant_id == tenant_id,
                Vehicle.id.in_(vehicle_ids),
            )
        )).scalars().all()
        vehicles = {v.id: v for v in rows}

    customer_ids = list({v.customer_id for v in vehicles.values() if v.customer_id})
    brand_ids = list({v.brand_id for v in vehicles.values() if v.brand_id})
    model_ids = list({v.model_id for v in vehicles.values() if v.model_id})

    customers: dict[int, Customer] = {}
    if customer_ids:
        rows = (await db.execute(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.id.in_(customer_ids),
            )
        )).scalars().all()
        customers = {c.id: c for c in rows}

    brands: dict[int, VehicleBrand] = {}
    if brand_ids:
        rows = (await db.execute(
            select(VehicleBrand).where(VehicleBrand.id.in_(brand_ids))
        )).scalars().all()
        brands = {b.id: b for b in rows}

    models: dict[int, VehicleModel] = {}
    if model_ids:
        rows = (await db.execute(
            select(VehicleModel).where(VehicleModel.id.in_(model_ids))
        )).scalars().all()
        models = {m.id: m for m in rows}

    mechanics: dict[int, Employee] = {}
    if mechanic_ids:
        rows = (await db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                Employee.id.in_(mechanic_ids),
            )
        )).scalars().all()
        mechanics = {e.id: e for e in rows}

    out: list[dict] = []
    for o in orders:
        v = vehicles.get(o.vehicle_id)
        vehicle_dict = None
        if v is not None:
            vehicle_dict = _vehicle_dict(
                v,
                customers.get(v.customer_id),
                brands.get(v.brand_id),
                models.get(v.model_id),
            )
        out.append({
            "id": o.id,
            "number": o.number,
            "vehicle_id": o.vehicle_id,
            "employee_id": o.employee_id,
            "mechanic_id": o.mechanic_id,
            "status": o.status,
            "total_amount": o.total_amount,
            "paid_amount": o.paid_amount,
            "created_at": o.created_at,
            "completed_at": o.completed_at,
            "vehicle": vehicle_dict,
            "mechanic": mechanics.get(o.mechanic_id) if o.mechanic_id else None,
        })
    return out


async def _serialize_order(
    db: AsyncSession, order: Order, claims: TenantClaims, *, detail: bool
) -> dict:
    vehicle_dict = None
    v = await db.get(Vehicle, (claims.tenant_id, order.vehicle_id))
    if v is not None:
        cust = await db.get(Customer, (claims.tenant_id, v.customer_id))
        brand = await db.get(VehicleBrand, v.brand_id)
        model = await db.get(VehicleModel, v.model_id)
        vehicle_dict = _vehicle_dict(v, cust, brand, model)

    mechanic = None
    if order.mechanic_id:
        mechanic = await db.get(Employee, (claims.tenant_id, order.mechanic_id))

    base = {
        "id": order.id,
        "number": order.number,
        "vehicle_id": order.vehicle_id,
        "employee_id": order.employee_id,
        "mechanic_id": order.mechanic_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "paid_amount": order.paid_amount,
        "created_at": order.created_at,
        "completed_at": order.completed_at,
        "vehicle": vehicle_dict,
        "mechanic": mechanic,
    }
    if not detail:
        return base
    employee = await db.get(Employee, (claims.tenant_id, order.employee_id))
    base["employee"] = employee
    base["recommendations"] = order.recommendations
    base["comments"] = order.comments
    base["order_works"] = await _serialize_order_works(db, order.id)
    base["order_parts"] = await _serialize_order_parts(db, order.id)
    return base


def _resolve_employee_id(claims: TenantClaims) -> int:
    if claims.employee_id is None:
        raise BadRequestException(
            "JWT-токен не содержит employee_id — невозможно создать/завершить заказ"
        )
    return claims.employee_id


async def _writeoff_order_parts(
    db: AsyncSession, order: Order, claims: TenantClaims
) -> None:
    """Списать запчасти заказа со склада + создать OUTGOING-движения.

    Idempotent: если по этому заказу уже есть OUTGOING-движения — выходим
    (списание было раньше). Вызывается при первом переходе заказа в
    paid/completed; повторные вызовы — безопасный no-op.

    Если у запчасти в order_parts есть part_id, но в warehouse_items
    карточки нет — пропускаем (продавали «с воздуха», склада не было).
    Списываем даже в минус (продажа в долг) — admin потом разберётся
    через корректировку.
    """
    already = (await db.execute(
        select(func.count(WarehouseTransaction.id)).where(
            WarehouseTransaction.order_id == order.id,
            WarehouseTransaction.transaction_type == TransactionType.OUTGOING.value,
        )
    )).scalar_one()
    if already > 0:
        return

    employee_id = _resolve_employee_id(claims)

    parts = (await db.execute(
        select(OrderPart).where(OrderPart.order_id == order.id)
    )).scalars().all()

    for op in parts:
        if op.part_id is None:
            continue
        item = (await db.execute(
            select(WarehouseItem).where(WarehouseItem.part_id == op.part_id)
        )).scalar_one_or_none()
        if item is None:
            continue
        qty = Decimal(str(op.quantity))
        item.quantity = Decimal(str(item.quantity)) - qty
        db.add(WarehouseTransaction(
            tenant_id=claims.tenant_id,
            warehouse_item_id=item.id,
            transaction_type=TransactionType.OUTGOING.value,
            quantity=qty,
            price=op.price,
            order_id=order.id,
            employee_id=employee_id,
        ))
    await db.flush()


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
_STATUS_LABELS = {
    OrderStatus.NEW.value: "Новый",
    OrderStatus.ESTIMATION.value: "Проценка",
    OrderStatus.IN_PROGRESS.value: "В работе",
    OrderStatus.READY_FOR_PAYMENT.value: "Готов к оплате",
    OrderStatus.PAID.value: "Оплачен",
    OrderStatus.COMPLETED.value: "Завершён",
    OrderStatus.CANCELLED.value: "Отменён",
}


@router.get("/statuses", response_model=list[LabelValueItem])
def list_statuses() -> list[LabelValueItem]:
    return [
        LabelValueItem(value=s.value, label=_STATUS_LABELS[s.value])
        for s in OrderStatus
        if s != OrderStatus.COMPLETED  # COMPLETED устанавливается операцией завершения
    ]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
_SORT_COLUMNS = {
    "number": Order.number,
    "created_at": Order.created_at,
    "completed_at": Order.completed_at,
}


@router.get("/", response_model=OrderListResponse, responses=_auth)
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    date_from: Optional[date] = Query(None, description="Заказы с created_at ≥ этой даты"),
    date_to: Optional[date] = Query(None, description="Заказы с created_at ≤ этой даты"),
    search: Optional[str] = Query(None, description="Подстрока для поиска по номеру ЗН, госномеру, ФИО клиента, телефону, ФИО мастера"),
    sort_by: str = Query("created_at", description="Поле сортировки: number / created_at / completed_at"),
    sort_dir: str = Query("desc", description="Направление: asc / desc"),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    base = select(Order)
    if status_filter:
        base = base.where(Order.status == status_filter.value)
    if date_from is not None:
        base = base.where(func.date(Order.created_at) >= date_from)
    if date_to is not None:
        base = base.where(func.date(Order.created_at) <= date_to)
    if "mechanic" in claims.roles and not (set(claims.roles) & {"admin", "manager"}):
        if claims.employee_id is not None:
            base = base.where(Order.mechanic_id == claims.employee_id)

    q = (search or "").strip()
    if q:
        pattern = f"%{q}%"
        tenant_id = claims.tenant_id
        # Подзапросы по связанным таблицам — PG превращает их в semi-join,
        # дубликатов в результате не будет, COUNT остаётся корректным.
        vehicles_by_plate = (
            select(Vehicle.id).where(
                Vehicle.tenant_id == tenant_id,
                Vehicle.license_plate.ilike(pattern),
            )
        )
        vehicles_by_customer = (
            select(Vehicle.id)
            .join(
                Customer,
                and_(
                    Customer.tenant_id == Vehicle.tenant_id,
                    Customer.id == Vehicle.customer_id,
                ),
            )
            .where(
                Vehicle.tenant_id == tenant_id,
                or_(
                    Customer.full_name.ilike(pattern),
                    Customer.phone.ilike(pattern),
                ),
            )
        )
        mechanics_by_name = (
            select(Employee.id).where(
                Employee.tenant_id == tenant_id,
                Employee.full_name.ilike(pattern),
            )
        )
        base = base.where(
            or_(
                Order.number.ilike(pattern),
                Order.vehicle_id.in_(vehicles_by_plate),
                Order.vehicle_id.in_(vehicles_by_customer),
                Order.mechanic_id.in_(mechanics_by_name),
            )
        )

    total = await db.scalar(
        select(func.count()).select_from(base.subquery())
    )

    sort_col = _SORT_COLUMNS.get(sort_by, Order.created_at)
    order_clause = sort_col.asc() if sort_dir == "asc" else sort_col.desc()
    # Стабильный тай-брейкер: id desc — для одинаковых ключей сортировки.
    page_stmt = (
        base.order_by(order_clause, Order.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await db.execute(page_stmt)).scalars().all())
    items = await _serialize_orders_bulk(db, rows, claims)
    return {"items": items, "total": int(total or 0)}


@router.get(
    "/{order_id}",
    response_model=OrderDetail,
    responses={**_auth, 403: {"model": ErrorResponse}, **_404},
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")
    if "mechanic" in claims.roles and not (set(claims.roles) & {"admin", "manager"}):
        if claims.employee_id is not None and order.mechanic_id != claims.employee_id:
            raise HTTPException(status_code=403, detail="Нет доступа к этому заказ-наряду")
    return await _serialize_order(db, order, claims, detail=True)


@router.post(
    "/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, 400: {"model": ErrorResponse}},
)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    employee_id = _resolve_employee_id(claims)

    if await db.get(Vehicle, (claims.tenant_id, body.vehicle_id)) is None:
        raise NotFoundException("Транспортное средство не найдено")

    await _validate_work_refs(db, body.order_works)
    await _validate_part_refs(db, body.order_parts)

    number = await _next_order_number(db)
    total_works = sum(
        (_line_total(w.price, w.quantity, w.discount) for w in body.order_works), Decimal(0)
    )
    total_parts = sum(
        (_line_total(p.price, p.quantity, p.discount) for p in body.order_parts), Decimal(0)
    )
    order = Order(
        tenant_id=claims.tenant_id,
        number=number,
        vehicle_id=body.vehicle_id,
        employee_id=employee_id,
        mechanic_id=body.mechanic_id,
        status=OrderStatus.NEW.value,
        total_amount=total_works + total_parts,
        paid_amount=Decimal(0),
        recommendations=body.recommendations,
        comments=body.comments,
    )
    db.add(order)
    await db.flush()

    for w in body.order_works:
        db.add(OrderWork(
            tenant_id=claims.tenant_id,
            order_id=order.id,
            work_id=w.work_id,
            work_name=w.work_name,
            mechanic_id=w.mechanic_id,
            quantity=w.quantity,
            price=w.price,
            discount=w.discount or Decimal(0),
            total=_line_total(w.price, w.quantity, w.discount),
        ))
    for p in body.order_parts:
        db.add(OrderPart(
            tenant_id=claims.tenant_id,
            order_id=order.id,
            part_id=p.part_id,
            part_name=p.part_name,
            article=p.article,
            quantity=p.quantity,
            price=p.price,
            discount=p.discount or Decimal(0),
            total=_line_total(p.price, p.quantity, p.discount),
        ))
    await db.flush()
    await db.refresh(order)
    return await _serialize_order(db, order, claims, detail=False)


@router.put("/{order_id}", response_model=OrderSchema, responses={**_write, **_404})
async def update_order_endpoint(
    order_id: int,
    body: OrderUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")

    data = body.model_dump(exclude_unset=True)

    if "order_works" in data and data["order_works"] is not None:
        await _validate_work_refs(db, body.order_works)
        await db.execute(delete(OrderWork).where(OrderWork.order_id == order.id))
        for w in body.order_works:
            db.add(OrderWork(
                tenant_id=claims.tenant_id, order_id=order.id,
                work_id=w.work_id, work_name=w.work_name, mechanic_id=w.mechanic_id,
                quantity=w.quantity, price=w.price, discount=w.discount or Decimal(0),
                total=_line_total(w.price, w.quantity, w.discount),
            ))
        await db.flush()
        data.pop("order_works")
    if "order_parts" in data and data["order_parts"] is not None:
        await _validate_part_refs(db, body.order_parts)
        await db.execute(delete(OrderPart).where(OrderPart.order_id == order.id))
        for p in body.order_parts:
            db.add(OrderPart(
                tenant_id=claims.tenant_id, order_id=order.id,
                part_id=p.part_id, part_name=p.part_name, article=p.article,
                quantity=p.quantity, price=p.price, discount=p.discount or Decimal(0),
                total=_line_total(p.price, p.quantity, p.discount),
            ))
        await db.flush()
        data.pop("order_parts")

    # Запрещаем именно *смену* status на завершающие — но no-op (тот же статус)
    # пропускаем: фронт обычно шлёт всю модель целиком при «Сохранить».
    if "status" in data and data["status"] is not None:
        new_status = data["status"].value if hasattr(data["status"], "value") else data["status"]
        if new_status != order.status:
            if new_status == OrderStatus.COMPLETED.value:
                raise BadRequestException(
                    "Завершение заказа доступно только через POST /orders/{id}/complete"
                )
            if new_status == OrderStatus.PAID.value:
                raise BadRequestException(
                    "Статус «Оплачен» выставляется автоматически после регистрации платежа"
                )
            if new_status == OrderStatus.CANCELLED.value:
                raise BadRequestException(
                    "Отмена доступна только через POST /orders/{id}/cancel"
                )
        data["status"] = new_status

    for k, v in data.items():
        setattr(order, k, v)

    works_total = (
        await db.execute(
            text("SELECT COALESCE(SUM(total), 0) FROM app.order_works WHERE order_id = :oid"),
            {"oid": order.id},
        )
    ).scalar() or Decimal(0)
    parts_total = (
        await db.execute(
            text("SELECT COALESCE(SUM(total), 0) FROM app.order_parts WHERE order_id = :oid"),
            {"oid": order.id},
        )
    ).scalar() or Decimal(0)
    order.total_amount = Decimal(works_total) + Decimal(parts_total)

    await db.flush()
    await db.refresh(order)
    return await _serialize_order(db, order, claims, detail=False)


@router.post("/{order_id}/cancel", response_model=OrderSchema, responses={**_write, **_404})
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")
    order.status = OrderStatus.CANCELLED.value
    await db.flush()
    await db.refresh(order)
    return await _serialize_order(db, order, claims, detail=False)


@router.post(
    "/{order_id}/complete",
    response_model=OrderSchema,
    responses={**_write, 400: {"model": ErrorResponse}, **_404},
)
async def complete_order(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    _resolve_employee_id(claims)
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")

    if order.status == OrderStatus.COMPLETED.value:
        raise BadRequestException("Заказ-наряд уже завершён")
    if order.status == OrderStatus.CANCELLED.value:
        raise BadRequestException("Нельзя завершить отменённый заказ-наряд")
    if order.status != OrderStatus.PAID.value:
        raise BadRequestException(
            "Завершить заказ можно только после полной оплаты"
        )

    has_works = (await db.execute(
        select(func.count()).select_from(OrderWork).where(OrderWork.order_id == order.id)
    )).scalar_one()
    has_parts = (await db.execute(
        select(func.count()).select_from(OrderPart).where(OrderPart.order_id == order.id)
    )).scalar_one()
    if not has_works and not has_parts:
        raise BadRequestException(
            "Нельзя завершить пустой заказ-наряд: добавьте работы или запчасти"
        )

    order.status = OrderStatus.COMPLETED.value
    order.completed_at = datetime.now(timezone.utc)
    await db.flush()
    # Списать запчасти со склада (idempotent — если paid уже списал, no-op).
    await _writeoff_order_parts(db, order, claims)
    await db.refresh(order)
    return await _serialize_order(db, order, claims, detail=False)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_admin, **_404},
)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
) -> Response:
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")
    await db.execute(delete(Payment).where(Payment.order_id == order_id))
    await db.delete(order)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Manual payments (Wave 4c)
# ---------------------------------------------------------------------------
@router.get(
    "/{order_id}/payments",
    response_model=list[PaymentSchema],
    responses={**_write, **_404},
)
async def list_order_payments(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    if await db.get(Order, (claims.tenant_id, order_id)) is None:
        raise NotFoundException("Заказ-наряд не найден")
    rows = (await db.execute(
        select(Payment).where(Payment.order_id == order_id).order_by(Payment.id)
    )).scalars().all()
    return list(rows)


@router.post(
    "/{order_id}/payments",
    response_model=PaymentSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, 400: {"model": ErrorResponse}, **_404},
)
async def create_order_payment(
    order_id: int,
    body: PaymentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    if body.order_id != order_id:
        raise BadRequestException(
            "order_id в path и в теле запроса не совпадают"
        )

    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")

    method = body.payment_method.value if hasattr(body.payment_method, "value") else body.payment_method
    payment = Payment(
        tenant_id=claims.tenant_id,
        order_id=order_id,
        amount=body.amount,
        payment_method=method,
        status=PaymentStatus.SUCCEEDED.value,  # manual = моментально succeeded
    )
    db.add(payment)
    await db.flush()

    # Обновляем paid_amount + статус заказа.
    new_paid = Decimal(str(order.paid_amount)) + Decimal(str(body.amount))
    order.paid_amount = new_paid
    did_become_paid = False
    if new_paid >= Decimal(str(order.total_amount)) and order.status not in (
        OrderStatus.PAID.value, OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value
    ):
        order.status = OrderStatus.PAID.value
        did_become_paid = True

    if did_become_paid:
        # При первом переходе заказа в paid — списываем запчасти со склада.
        # Если потом будет /complete — там стоит idempotent-проверка, повторно
        # не спишет.
        await _writeoff_order_parts(db, order, claims)

    # Cashflow income — если есть активный счёт и системная категория «Оплата заказа».
    account = (await db.execute(
        select(Account).where(Account.is_active.is_(True)).order_by(Account.id).limit(1)
    )).scalar_one_or_none()
    cat = (await db.execute(
        select(TransactionCategory).where(
            TransactionCategory.is_system.is_(True),
            TransactionCategory.name == "Оплата заказа",
            TransactionCategory.transaction_type == CashflowTransactionType.INCOME.value,
        )
    )).scalar_one_or_none()
    if account is not None and cat is not None:
        db.add(CashTransaction(
            tenant_id=claims.tenant_id,
            transaction_type=CashflowTransactionType.INCOME.value,
            account_id=account.id,
            to_account_id=None,
            category_id=cat.id,
            amount=body.amount,
            description=f"Оплата заказа {order.number} ({method})",
            transaction_date=datetime.now(timezone.utc),
            order_id=order.id,
            payment_id=payment.id,
        ))

    _log_payment_snapshot(db, claims.tenant_id, payment, claims.employee_id)
    await db.flush()
    await db.refresh(payment)
    return payment


def _log_payment_snapshot(
    db: AsyncSession,
    tenant_id,
    payment: Payment,
    employee_id: int | None,
) -> None:
    """Append-only снимок состояния платежа после операции."""
    db.add(PaymentLog(
        tenant_id=tenant_id,
        payment_id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        yookassa_payment_id=payment.yookassa_payment_id,
        status=payment.status,
        employee_id=employee_id,
    ))


async def _cancel_payment_row(
    db: AsyncSession,
    tenant_id,
    order: Order,
    payment: Payment,
) -> None:
    """Отметить платёж как cancelled, вычесть из paid_amount, снести cashflow.

    Статус заказа не меняем — этим занимается вызывающий эндпоинт после того,
    как обработаны все целевые платежи (важно для cancel-all).
    """
    payment.status = PaymentStatus.CANCELLED.value
    await db.execute(
        delete(CashTransaction).where(CashTransaction.payment_id == payment.id)
    )
    new_paid = Decimal(str(order.paid_amount or 0)) - Decimal(str(payment.amount))
    if new_paid < 0:
        new_paid = Decimal(0)
    order.paid_amount = new_paid


def _revert_status_if_unpaid(order: Order) -> None:
    """Если paid_amount стал меньше total и заказ был в PAID/COMPLETED —
    откатываем в READY_FOR_PAYMENT (работы сделаны, но не оплачены)."""
    if Decimal(str(order.paid_amount or 0)) < Decimal(str(order.total_amount or 0)) and (
        order.status in (OrderStatus.PAID.value, OrderStatus.COMPLETED.value)
    ):
        order.status = OrderStatus.READY_FOR_PAYMENT.value
        order.completed_at = None


@router.post(
    "/{order_id}/payments/{payment_id}/cancel",
    response_model=PaymentSchema,
    responses={**_admin, 400: {"model": ErrorResponse}, **_404},
)
async def cancel_order_payment(
    order_id: int,
    payment_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")
    payment = await db.get(Payment, (claims.tenant_id, payment_id))
    if payment is None or payment.order_id != order_id:
        raise NotFoundException("Платёж не найден")
    if payment.status != PaymentStatus.SUCCEEDED.value:
        raise BadRequestException("Платёж уже отменён или не был успешным")

    await _cancel_payment_row(db, claims.tenant_id, order, payment)
    _revert_status_if_unpaid(order)
    _log_payment_snapshot(db, claims.tenant_id, payment, claims.employee_id)

    await db.flush()
    await db.refresh(payment)
    return payment


@router.post(
    "/{order_id}/payments/cancel-all",
    response_model=list[PaymentSchema],
    responses={**_admin, **_404},
)
async def cancel_all_order_payments(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    order = await db.get(Order, (claims.tenant_id, order_id))
    if order is None:
        raise NotFoundException("Заказ-наряд не найден")

    payments = (await db.execute(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.SUCCEEDED.value,
        ).order_by(Payment.id)
    )).scalars().all()

    for p in payments:
        await _cancel_payment_row(db, claims.tenant_id, order, p)
        _log_payment_snapshot(db, claims.tenant_id, p, claims.employee_id)
    _revert_status_if_unpaid(order)

    await db.flush()
    for p in payments:
        await db.refresh(p)
    return list(payments)


@router.get(
    "/{order_id}/payments/log",
    response_model=list[PaymentLogEntry],
    responses={**_write, **_404},
)
async def get_order_payment_log(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    """История всех операций над платежами заказа (хронологически).

    Каждая строка — снимок состояния платежа после действия (создание / отмена).
    Действие определяется на фронте по разнице со status предыдущего снимка.
    """
    if await db.get(Order, (claims.tenant_id, order_id)) is None:
        raise NotFoundException("Заказ-наряд не найден")

    rows = (await db.execute(
        select(
            PaymentLog.id,
            PaymentLog.payment_id,
            PaymentLog.order_id,
            PaymentLog.amount,
            PaymentLog.payment_method,
            PaymentLog.status,
            PaymentLog.employee_id,
            Employee.full_name,
            Employee.position,
            PaymentLog.created_at,
        )
        .outerjoin(Employee, (Employee.id == PaymentLog.employee_id) & (Employee.tenant_id == PaymentLog.tenant_id))
        .where(PaymentLog.order_id == order_id)
        .order_by(PaymentLog.created_at, PaymentLog.id)
    )).all()

    return [
        PaymentLogEntry(
            id=r[0],
            payment_id=r[1],
            order_id=r[2],
            amount=r[3],
            payment_method=r[4],
            status=r[5],
            employee_id=r[6],
            employee_name=r[7],
            employee_position=r[8].value if hasattr(r[8], "value") else r[8],
            created_at=r[9],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Печать (PDF): заказ-наряд и акт выполненных работ
# ---------------------------------------------------------------------------
@router.get("/{order_id}/print", responses={**_auth, **_404})
async def print_order(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    """PDF заказ-наряда. pdf_service использует sync Session, поэтому
    рендерим в threadpool с отдельной sync-сессией под тем же тенантом."""
    if await db.get(Order, (claims.tenant_id, order_id)) is None:
        raise NotFoundException("Заказ-наряд не найден")

    def _render() -> bytes:
        with sync_tenant_session(claims.tenant_id) as sync_db:
            return generate_order_pdf(sync_db, order_id)

    pdf_bytes = await run_in_threadpool(_render)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="order-{order_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{order_id}/print-act", responses={**_auth, **_404})
async def print_order_act(
    order_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    """PDF акта выполненных работ по заказ-наряду."""
    if await db.get(Order, (claims.tenant_id, order_id)) is None:
        raise NotFoundException("Заказ-наряд не найден")

    def _render() -> bytes:
        with sync_tenant_session(claims.tenant_id) as sync_db:
            return generate_act_pdf(sync_db, order_id)

    pdf_bytes = await run_in_threadpool(_render)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="act-{order_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )
