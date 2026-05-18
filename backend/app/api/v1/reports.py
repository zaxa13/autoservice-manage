"""Отчёты — async aggregations на shared-DB.

4 endpoint'а:
- GET /reports/revenue — выручка по дням / категориям работ / методам оплаты.
- GET /reports/mechanics — per-mechanic stats + team totals + salary за период.
- GET /reports/orders — список заказ-нарядов с деталями + by_status counts.
- GET /reports/parts — топ запчастей по выручке + маржа + low-stock.

Все агрегации идут под RLS (фильтр по тенанту автоматический).
Period max 366 дней.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.order import Order, OrderPart, OrderStatus, OrderWork
from app.models.part import Part
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.salary import Salary
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.models.warehouse import WarehouseItem
from app.models.work import Work
from app.schemas.reports import (
    MechanicReportItem,
    MechanicsReportResponse,
    OrderReportItem,
    OrdersReportResponse,
    PartUsageItem,
    PartsReportResponse,
    RevenueByDayItem,
    RevenueByPaymentMethodItem,
    RevenueByWorkCategoryItem,
    RevenueReportResponse,
)
from app.schemas.responses import ErrorResponse

router = APIRouter()

_400 = {400: {"model": ErrorResponse, "description": "Некорректный диапазон дат"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}


_STATUS_LABELS = {
    "new": "Новый",
    "estimation": "Проценка",
    "in_progress": "В работе",
    "ready_for_payment": "Готов к оплате",
    "paid": "Оплачен",
    "completed": "Завершён",
    "cancelled": "Отменён",
}

_WORK_CATEGORY_LABELS = {
    "diagnostics": "Диагностика",
    "engine": "Двигатель",
    "transmission": "Трансмиссия",
    "suspension": "Подвеска",
    "brakes": "Тормоза",
    "electrical": "Электрика",
    "cooling": "Охлаждение",
    "fuel_system": "Топливная",
    "exhaust": "Выхлоп",
    "climate": "Климат",
    "maintenance": "ТО",
    "body_work": "Кузовные",
    "painting": "Покраска",
    "tire_service": "Шиномонтаж",
    "glass": "Стёкла",
    "repair": "Ремонт",
    "other": "Прочее",
}

_PAYMENT_METHOD_LABELS = {
    "cash": "Наличные",
    "card": "Карта",
    "yookassa": "ЮКасса",
}

_PART_CATEGORY_LABELS = {
    "engine": "Двигатель",
    "transmission": "Трансмиссия",
    "suspension": "Подвеска",
    "brakes": "Тормоза",
    "electrical": "Электрика",
    "body": "Кузов",
    "consumables": "Расходники",
    "other": "Прочее",
}


def _validate_range(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise HTTPException(400, "date_from не может быть позже date_to")
    if (date_to - date_from).days > 366:
        raise HTTPException(400, "Период не может превышать 366 дней")


# ---------------------------------------------------------------------------
# Revenue report
# ---------------------------------------------------------------------------
@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    responses={**_auth, **_400},
)
async def revenue_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    _validate_range(date_from, date_to)

    # Подзапрос: id заказов, завершённых в периоде (status=completed, completed_at в диапазоне).
    completed_orders_subq = (
        select(Order.id).where(
            Order.status == "completed",
            Order.completed_at.is_not(None),
            func.date(Order.completed_at) >= date_from,
            func.date(Order.completed_at) <= date_to,
        )
    ).scalar_subquery()

    # 1. Кол-во завершённых заказов в периоде.
    total_orders = int((await db.execute(
        select(func.count(Order.id)).where(
            Order.status == "completed",
            Order.completed_at.is_not(None),
            func.date(Order.completed_at) >= date_from,
            func.date(Order.completed_at) <= date_to,
        )
    )).scalar() or 0)

    # 2. Выручка = сумма успешных платежей по этим заказам.
    total_revenue = float((
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == PaymentStatus.SUCCEEDED.value,
                Payment.order_id.in_(completed_orders_subq),
            )
        )
    ).scalar() or 0)

    avg_check = total_revenue / total_orders if total_orders else 0.0

    # 3. По дням — платежи этих заказов, группировка по дате платежа.
    rows = (await db.execute(
        select(
            func.date(Payment.created_at).label("d"),
            func.sum(Payment.amount),
            func.count(func.distinct(Payment.order_id)),
        ).where(
            Payment.status == PaymentStatus.SUCCEEDED.value,
            Payment.order_id.in_(completed_orders_subq),
        ).group_by(func.date(Payment.created_at)).order_by(func.date(Payment.created_at))
    )).all()
    by_day = [
        RevenueByDayItem(date=str(r[0]), revenue=float(r[1] or 0), orders_count=int(r[2] or 0))
        for r in rows
    ]

    # 4. По категориям работ — только OrderWork завершённых заказов.
    rows = (await db.execute(
        select(
            Work.category,
            func.coalesce(func.sum(OrderWork.total), 0),
            func.count(func.distinct(OrderWork.order_id)),
        )
        .outerjoin(Work, (Work.id == OrderWork.work_id) & (Work.tenant_id == OrderWork.tenant_id))
        .where(OrderWork.order_id.in_(completed_orders_subq))
        .group_by(Work.category)
    )).all()
    by_work_category = [
        RevenueByWorkCategoryItem(
            category=r[0] or "other",
            category_label=_WORK_CATEGORY_LABELS.get(r[0] or "other", "Прочее"),
            revenue=float(r[1] or 0),
            orders_count=int(r[2] or 0),
        )
        for r in rows
    ]

    # 5. По методам оплаты — те же платежи.
    rows = (await db.execute(
        select(
            Payment.payment_method,
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        ).where(
            Payment.status == PaymentStatus.SUCCEEDED.value,
            Payment.order_id.in_(completed_orders_subq),
        ).group_by(Payment.payment_method)
    )).all()
    by_payment_method = [
        RevenueByPaymentMethodItem(
            method=r[0],
            method_label=_PAYMENT_METHOD_LABELS.get(r[0], r[0]),
            amount=float(r[1] or 0),
            payments_count=int(r[2] or 0),
        )
        for r in rows
    ]

    return RevenueReportResponse(
        date_from=str(date_from), date_to=str(date_to),
        total_revenue=total_revenue, total_orders=total_orders,
        avg_check=avg_check,
        by_day=by_day, by_work_category=by_work_category,
        by_payment_method=by_payment_method,
    )


# ---------------------------------------------------------------------------
# Mechanics report
# ---------------------------------------------------------------------------
@router.get(
    "/mechanics",
    response_model=MechanicsReportResponse,
    responses={**_auth, **_400},
)
async def mechanics_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    _validate_range(date_from, date_to)

    # Завершённые заказы в периоде (по completed_at). Только status=completed —
    # `paid` не учитывается, т.к. заказ ещё не закрыт.
    period_orders = (await db.execute(
        select(Order).where(
            Order.mechanic_id.is_not(None),
            Order.status == "completed",
            Order.completed_at.is_not(None),
            func.date(Order.completed_at) >= date_from,
            func.date(Order.completed_at) <= date_to,
        )
    )).scalars().all()

    completed_by_mech: dict[int, list] = defaultdict(list)
    for o in period_orders:
        completed_by_mech[o.mechanic_id].append(o)

    # Снимок in_progress на текущий момент (без даты).
    active_now = (await db.execute(
        select(Order.mechanic_id, func.count(Order.id))
        .where(Order.mechanic_id.is_not(None), Order.status == "in_progress")
        .group_by(Order.mechanic_id)
    )).all()
    active_now_map = {r[0]: int(r[1]) for r in active_now}

    mechanic_ids = set(completed_by_mech.keys()) | set(active_now_map.keys())

    # Выручка и кол-во работ — только по OrderWork (без запчастей) из этих
    # завершённых заказов. Запчасти (OrderPart) в выручку механика НЕ входят.
    works_sum_by_order: dict[int, float] = {}
    works_cnt_by_order: dict[int, int] = {}
    all_order_ids = [o.id for orders in completed_by_mech.values() for o in orders]
    if all_order_ids:
        rows = (await db.execute(
            select(
                OrderWork.order_id,
                func.coalesce(func.sum(OrderWork.total), 0),
                func.count(OrderWork.id),
            )
            .where(OrderWork.order_id.in_(all_order_ids))
            .group_by(OrderWork.order_id)
        )).all()
        works_sum_by_order = {r[0]: float(r[1] or 0) for r in rows}
        works_cnt_by_order = {r[0]: int(r[2] or 0) for r in rows}

    # Salary за период (если есть).
    salary_map: dict[int, float] = {}
    if mechanic_ids:
        rows = (await db.execute(
            select(Salary.employee_id, func.sum(Salary.total)).where(
                Salary.employee_id.in_(mechanic_ids),
                Salary.period_start >= date_from,
                Salary.period_end <= date_to,
            ).group_by(Salary.employee_id)
        )).all()
        salary_map = {r[0]: float(r[1] or 0) for r in rows}

    emp_map = {}
    if mechanic_ids:
        emp_map = {
            e.id: e
            for e in (
                await db.execute(select(Employee).where(Employee.id.in_(mechanic_ids)))
            ).scalars()
        }

    mechanics = []
    team_total_revenue = 0.0
    team_total_orders = 0
    for mid in mechanic_ids:
        emp = emp_map.get(mid)
        if not emp:
            continue
        completed = completed_by_mech.get(mid, [])
        revenue = sum(works_sum_by_order.get(o.id, 0.0) for o in completed)
        works_count = sum(works_cnt_by_order.get(o.id, 0) for o in completed)
        cnt = len(completed)
        team_total_revenue += revenue
        team_total_orders += cnt
        avg_check = revenue / cnt if cnt else 0.0
        mechanics.append(MechanicReportItem(
            employee_id=mid, full_name=emp.full_name,
            orders_completed=cnt,
            orders_in_progress=active_now_map.get(mid, 0),
            revenue=revenue, avg_check=avg_check,
            works_count=works_count,
            salary_total=salary_map.get(mid),
        ))
    mechanics.sort(key=lambda x: x.revenue, reverse=True)

    team_avg = team_total_revenue / team_total_orders if team_total_orders else 0.0

    return MechanicsReportResponse(
        date_from=str(date_from), date_to=str(date_to),
        mechanics=mechanics,
        team_total_revenue=team_total_revenue,
        team_total_orders=team_total_orders,
        team_avg_check=team_avg,
    )


# ---------------------------------------------------------------------------
# Orders report
# ---------------------------------------------------------------------------
@router.get(
    "/orders",
    response_model=OrdersReportResponse,
    responses={**_auth, **_400},
)
async def orders_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    status_filter: Optional[str] = Query(None, alias="status",
        pattern="^(new|estimation|in_progress|ready_for_payment|paid|completed|cancelled)$"),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    _validate_range(date_from, date_to)

    stmt = (
        select(Order).where(
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        ).order_by(Order.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    orders = (await db.execute(stmt)).scalars().all()

    total_amount = sum(float(o.total_amount or 0) for o in orders)
    total_paid = sum(float(o.paid_amount or 0) for o in orders)

    # Counts by status.
    rows = (await db.execute(
        select(Order.status, func.count(Order.id))
        .where(
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .group_by(Order.status)
    )).all()
    by_status = [
        {"status": r[0], "status_label": _STATUS_LABELS.get(r[0], r[0]), "count": int(r[1])}
        for r in rows
    ]

    # Bulk fetch refs.
    if not orders:
        return OrdersReportResponse(
            date_from=str(date_from), date_to=str(date_to),
            total_count=0, total_amount=0, total_paid=0,
            by_status=[], orders=[],
        )

    vehicle_ids = {o.vehicle_id for o in orders}
    mech_ids = {o.mechanic_id for o in orders if o.mechanic_id}
    vehicles_rows = (await db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)))).scalars().all()
    vmap = {v.id: v for v in vehicles_rows}
    cust_ids = {v.customer_id for v in vehicles_rows}
    brand_ids = {v.brand_id for v in vehicles_rows}
    model_ids = {v.model_id for v in vehicles_rows}
    cmap = {
        c.id: c for c in (await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))).scalars()
    } if cust_ids else {}
    bmap = {
        b.id: b for b in (await db.execute(select(VehicleBrand).where(VehicleBrand.id.in_(brand_ids)))).scalars()
    } if brand_ids else {}
    mmap = {
        m.id: m for m in (await db.execute(select(VehicleModel).where(VehicleModel.id.in_(model_ids)))).scalars()
    } if model_ids else {}
    emap = {
        e.id: e for e in (await db.execute(select(Employee).where(Employee.id.in_(mech_ids)))).scalars()
    } if mech_ids else {}

    # Works/parts totals per order.
    order_ids = [o.id for o in orders]
    works_rows = (await db.execute(
        select(OrderWork.order_id, func.sum(OrderWork.total))
        .where(OrderWork.order_id.in_(order_ids))
        .group_by(OrderWork.order_id)
    )).all()
    works_total_by_order = {r[0]: float(r[1] or 0) for r in works_rows}
    parts_rows = (await db.execute(
        select(OrderPart.order_id, func.sum(OrderPart.total))
        .where(OrderPart.order_id.in_(order_ids))
        .group_by(OrderPart.order_id)
    )).all()
    parts_total_by_order = {r[0]: float(r[1] or 0) for r in parts_rows}

    items = []
    for o in orders:
        v = vmap.get(o.vehicle_id)
        cust = cmap.get(v.customer_id) if v else None
        brand = bmap.get(v.brand_id) if v else None
        model = mmap.get(v.model_id) if v else None
        mech = emap.get(o.mechanic_id) if o.mechanic_id else None
        veh_info = None
        if brand or model or (v and v.license_plate):
            parts = []
            if brand:
                parts.append(brand.name)
            if model:
                parts.append(model.name)
            if v and v.license_plate:
                parts.append(v.license_plate)
            veh_info = " ".join(parts)
        items.append(OrderReportItem(
            id=o.id, number=o.number,
            status=o.status, status_label=_STATUS_LABELS.get(o.status, o.status),
            created_at=o.created_at.isoformat(),
            completed_at=o.completed_at.isoformat() if o.completed_at else None,
            customer_name=cust.full_name if cust else None,
            vehicle_info=veh_info,
            mechanic_name=mech.full_name if mech else None,
            total_amount=float(o.total_amount or 0),
            paid_amount=float(o.paid_amount or 0),
            works_total=works_total_by_order.get(o.id, 0.0),
            parts_total=parts_total_by_order.get(o.id, 0.0),
        ))

    return OrdersReportResponse(
        date_from=str(date_from), date_to=str(date_to),
        total_count=len(orders),
        total_amount=total_amount, total_paid=total_paid,
        by_status=by_status, orders=items,
    )


# ---------------------------------------------------------------------------
# Parts report
# ---------------------------------------------------------------------------
@router.get(
    "/parts",
    response_model=PartsReportResponse,
    responses={**_auth, **_400},
)
async def parts_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    _validate_range(date_from, date_to)

    # Использование запчастей через order_parts → orders, завершённые в периоде.
    rows = (await db.execute(
        select(
            OrderPart.part_id,
            func.coalesce(func.sum(OrderPart.quantity), 0).label("qty"),
            func.coalesce(func.sum(OrderPart.total), 0).label("revenue"),
            func.count(func.distinct(OrderPart.order_id)).label("orders_cnt"),
        )
        .join(Order, (Order.id == OrderPart.order_id) & (Order.tenant_id == OrderPart.tenant_id))
        .where(
            OrderPart.part_id.is_not(None),
            Order.status == "completed",
            Order.completed_at.is_not(None),
            func.date(Order.completed_at) >= date_from,
            func.date(Order.completed_at) <= date_to,
        )
        .group_by(OrderPart.part_id)
    )).all()

    part_ids = [r[0] for r in rows]
    pmap: dict[int, Part] = {}
    if part_ids:
        pmap = {
            p.id: p
            for p in (
                await db.execute(select(Part).where(Part.id.in_(part_ids)))
            ).scalars()
        }
    # Stock per part.
    stock_map: dict[int, float] = {}
    if part_ids:
        srows = (await db.execute(
            select(WarehouseItem.part_id, WarehouseItem.quantity)
            .where(WarehouseItem.part_id.in_(part_ids))
        )).all()
        stock_map = {r[0]: float(r[1] or 0) for r in srows}

    items = []
    total_revenue = 0.0
    total_qty = 0.0
    total_cost = 0.0
    for r in rows:
        pid = r[0]
        part = pmap.get(pid)
        if part is None:
            continue
        qty = float(r[1] or 0)
        rev = float(r[2] or 0)
        purchase = float(part.purchase_price_last or 0)
        cost = qty * purchase
        margin = rev - cost
        margin_pct = (margin / rev * 100) if rev else 0.0
        items.append(PartUsageItem(
            part_id=pid,
            part_name=part.name,
            part_number=part.part_number,
            category=part.category,
            category_label=_PART_CATEGORY_LABELS.get(part.category, part.category),
            total_quantity=qty,
            total_revenue=rev,
            total_cost=cost,
            total_margin=margin,
            margin_pct=round(margin_pct, 1),
            orders_count=int(r[3] or 0),
            current_stock=stock_map.get(pid, 0.0),
        ))
        total_revenue += rev
        total_qty += qty
        total_cost += cost

    items.sort(key=lambda x: x.total_revenue, reverse=True)
    top_parts = items[:50]

    # Low stock — независимо от периода.
    low_rows = (await db.execute(
        select(WarehouseItem).where(WarehouseItem.quantity < WarehouseItem.min_quantity)
    )).scalars().all()
    low_stock_parts: list[PartUsageItem] = []
    if low_rows:
        ids = {wi.part_id for wi in low_rows}
        ext_parts = {
            p.id: p
            for p in (await db.execute(select(Part).where(Part.id.in_(ids)))).scalars()
        }
        for wi in low_rows:
            p = ext_parts.get(wi.part_id)
            if p is None:
                continue
            low_stock_parts.append(PartUsageItem(
                part_id=p.id, part_name=p.name, part_number=p.part_number,
                category=p.category,
                category_label=_PART_CATEGORY_LABELS.get(p.category, p.category),
                total_quantity=0.0, total_revenue=0.0, total_cost=0.0,
                total_margin=0.0, margin_pct=0.0, orders_count=0,
                current_stock=float(wi.quantity or 0),
            ))

    total_margin = total_revenue - total_cost
    total_margin_pct = (total_margin / total_revenue * 100) if total_revenue else 0.0

    return PartsReportResponse(
        date_from=str(date_from), date_to=str(date_to),
        total_parts_revenue=total_revenue,
        total_quantity_sold=total_qty,
        total_parts_cost=total_cost,
        total_parts_margin=total_margin,
        total_margin_pct=round(total_margin_pct, 1),
        top_parts=top_parts,
        low_stock_parts=low_stock_parts,
    )
