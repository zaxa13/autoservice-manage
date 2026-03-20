from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date
from typing import List, Tuple

from app.models.order import Order, OrderWork, OrderPart, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.work import Work
from app.models.part import Part
from app.models.warehouse import WarehouseItem
from app.models.employee import Employee
from app.models.salary import Salary, SalaryStatus
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from app.models.vehicle_brand import VehicleBrand, VehicleModel


_WORK_CATEGORY_LABELS: dict[str, str] = {
    "diagnostics": "Диагностика",
    "engine": "Двигатель",
    "transmission": "Трансмиссия",
    "suspension": "Подвеска",
    "brakes": "Тормоза",
    "electrical": "Электрика",
    "cooling": "Охлаждение",
    "fuel_system": "Топливная система",
    "exhaust": "Выхлоп",
    "climate": "Климат",
    "maintenance": "ТО",
    "body_work": "Кузов",
    "painting": "Покраска",
    "tire_service": "Шиномонтаж",
    "glass": "Стекло",
    "repair": "Ремонт",
    "other": "Прочее",
}

_PART_CATEGORY_LABELS: dict[str, str] = {
    "engine": "Двигатель",
    "transmission": "Трансмиссия",
    "suspension": "Подвеска",
    "brakes": "Тормоза",
    "electrical": "Электрика",
    "body": "Кузов",
    "consumables": "Расходники",
    "other": "Прочее",
}

_PAYMENT_METHOD_LABELS: dict[str, str] = {
    "cash": "Наличные",
    "card": "Банковская карта",
    "yookassa": "ЮKassa",
}

_ORDER_STATUS_LABELS: dict[str, str] = {
    "new": "Новый",
    "estimation": "Проценка",
    "in_progress": "В работе",
    "ready_for_payment": "Готов к оплате",
    "paid": "Оплачен",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


def get_revenue_report_data(
    db: Session,
    date_from: date,
    date_to: date,
) -> dict:
    """Aggregate revenue data for the given date range."""

    # Total revenue from succeeded payments
    total_revenue = float(
        db.query(func.sum(Payment.amount))
        .filter(
            Payment.status == PaymentStatus.SUCCEEDED,
            func.date(Payment.created_at) >= date_from,
            func.date(Payment.created_at) <= date_to,
        )
        .scalar() or 0
    )

    # Total paid/completed orders in period
    total_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.status.in_(["paid", "completed"]),
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .scalar() or 0
    )

    avg_check = total_revenue / total_orders if total_orders else 0.0

    # Revenue by day
    rows_by_day = (
        db.query(
            func.date(Payment.created_at).label("day"),
            func.sum(Payment.amount).label("revenue"),
            func.count(Payment.id).label("payments_count"),
        )
        .filter(
            Payment.status == PaymentStatus.SUCCEEDED,
            func.date(Payment.created_at) >= date_from,
            func.date(Payment.created_at) <= date_to,
        )
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
        .all()
    )
    by_day = [
        {
            "date": str(r.day),
            "revenue": float(r.revenue or 0),
            "orders_count": int(r.payments_count or 0),
        }
        for r in rows_by_day
    ]

    # Revenue by work category (via order_works → works)
    rows_work_cat = (
        db.query(
            Work.category.label("category"),
            func.sum(OrderWork.total).label("revenue"),
            func.count(func.distinct(OrderWork.order_id)).label("orders_count"),
        )
        .join(OrderWork, OrderWork.work_id == Work.id)
        .join(Order, Order.id == OrderWork.order_id)
        .filter(
            Order.status.in_(["paid", "completed"]),
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .group_by(Work.category)
        .order_by(func.sum(OrderWork.total).desc())
        .all()
    )
    by_work_category = [
        {
            "category": r.category.value if hasattr(r.category, "value") else str(r.category),
            "category_label": _WORK_CATEGORY_LABELS.get(
                r.category.value if hasattr(r.category, "value") else str(r.category),
                r.category.value if hasattr(r.category, "value") else str(r.category),
            ),
            "revenue": float(r.revenue or 0),
            "orders_count": int(r.orders_count or 0),
        }
        for r in rows_work_cat
    ]

    # Revenue by payment method
    rows_method = (
        db.query(
            Payment.payment_method.label("method"),
            func.sum(Payment.amount).label("amount"),
            func.count(Payment.id).label("payments_count"),
        )
        .filter(
            Payment.status == PaymentStatus.SUCCEEDED,
            func.date(Payment.created_at) >= date_from,
            func.date(Payment.created_at) <= date_to,
        )
        .group_by(Payment.payment_method)
        .order_by(func.sum(Payment.amount).desc())
        .all()
    )
    by_payment_method = [
        {
            "method": r.method.value if hasattr(r.method, "value") else str(r.method),
            "method_label": _PAYMENT_METHOD_LABELS.get(
                r.method.value if hasattr(r.method, "value") else str(r.method),
                r.method.value if hasattr(r.method, "value") else str(r.method),
            ),
            "amount": float(r.amount or 0),
            "payments_count": int(r.payments_count or 0),
        }
        for r in rows_method
    ]

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "avg_check": round(avg_check, 2),
        "by_day": by_day,
        "by_work_category": by_work_category,
        "by_payment_method": by_payment_method,
    }


def get_mechanics_report_data(
    db: Session,
    date_from: date,
    date_to: date,
) -> dict:
    """Aggregate per-mechanic performance stats.

    Revenue is counted from order_works rows where mechanic_id matches the
    employee — this allows multiple mechanics on one order. Works without a
    mechanic_id fall back to the order-level mechanic_id so that existing
    data (created before the per-line mechanic feature) is still counted.
    """

    # Load all order_works for non-cancelled orders in the period
    work_rows = (
        db.query(OrderWork)
        .join(Order, Order.id == OrderWork.order_id)
        .filter(
            Order.status.in_(["in_progress", "ready_for_payment", "paid", "completed"]),
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .options(joinedload(OrderWork.mechanic))
        .all()
    )

    # Also need order-level mechanic_id as fallback
    orders_in_period = (
        db.query(Order)
        .filter(
            Order.status.in_(["in_progress", "ready_for_payment", "paid", "completed"]),
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .all()
    )
    order_mechanic_map: dict[int, int | None] = {o.id: o.mechanic_id for o in orders_in_period}
    order_status_map: dict[int, str] = {
        o.id: str(o.status.value if hasattr(o.status, "value") else o.status)
        for o in orders_in_period
    }

    # Group order_works by resolved mechanic
    # mechanic_id on the work line takes priority; fall back to order-level
    by_mechanic: dict[int, dict] = {}

    for w in work_rows:
        mid = w.mechanic_id or order_mechanic_map.get(w.order_id)
        if mid is None:
            continue
        if mid not in by_mechanic:
            by_mechanic[mid] = {
                "works": [],
                "order_ids_completed": set(),
                "order_ids_in_progress": set(),
            }
        by_mechanic[mid]["works"].append(w)
        status = order_status_map.get(w.order_id, "")
        if status in ("paid", "completed"):
            by_mechanic[mid]["order_ids_completed"].add(w.order_id)
        elif status == "in_progress":
            by_mechanic[mid]["order_ids_in_progress"].add(w.order_id)

    # Salary data
    salary_rows = (
        db.query(Salary.employee_id, func.sum(Salary.total).label("salary_total"))
        .filter(
            Salary.status.in_([SalaryStatus.CALCULATED, SalaryStatus.PAID]),
            Salary.period_start >= date_from,
            Salary.period_end <= date_to,
        )
        .group_by(Salary.employee_id)
        .all()
    )
    salary_map: dict[int, float] = {r.employee_id: float(r.salary_total or 0) for r in salary_rows}

    mechanic_ids = set(by_mechanic.keys())
    employees = db.query(Employee).filter(Employee.id.in_(mechanic_ids)).all() if mechanic_ids else []
    emp_map = {e.id: e for e in employees}

    mechanics = []
    for mid, data in by_mechanic.items():
        emp = emp_map.get(mid)
        if not emp:
            continue
        works = data["works"]
        # Revenue = sum of work line totals (only works, not parts)
        revenue = sum(float(w.total or 0) for w in works)
        orders_completed = len(data["order_ids_completed"])
        orders_in_progress = len(data["order_ids_in_progress"])
        total_orders = orders_completed + orders_in_progress
        avg_check = revenue / total_orders if total_orders else 0
        mechanics.append({
            "employee_id": mid,
            "full_name": emp.full_name,
            "orders_completed": orders_completed,
            "orders_in_progress": orders_in_progress,
            "revenue": round(revenue, 2),
            "avg_check": round(avg_check, 2),
            "works_count": len(works),
            "salary_total": salary_map.get(mid),
        })

    mechanics.sort(key=lambda x: x["revenue"], reverse=True)

    team_total_revenue = sum(m["revenue"] for m in mechanics)
    team_total_orders = sum(m["orders_completed"] + m["orders_in_progress"] for m in mechanics)
    team_avg_check = team_total_revenue / team_total_orders if team_total_orders else 0

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "mechanics": mechanics,
        "team_total_revenue": round(team_total_revenue, 2),
        "team_total_orders": team_total_orders,
        "team_avg_check": round(team_avg_check, 2),
    }


def get_orders_report_data(
    db: Session,
    date_from: date,
    date_to: date,
    status_filter: str | None = None,
) -> dict:
    """Detailed orders list with aggregates for the given date range."""

    query = (
        db.query(Order)
        .options(
            joinedload(Order.mechanic),
            joinedload(Order.vehicle).joinedload(Vehicle.customer),
            joinedload(Order.vehicle).joinedload(Vehicle.brand),
            joinedload(Order.vehicle).joinedload(Vehicle.vehicle_model),
            joinedload(Order.order_works),
            joinedload(Order.order_parts),
        )
        .filter(
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
    )
    if status_filter:
        query = query.filter(Order.status == status_filter)

    all_orders = query.order_by(Order.created_at.desc()).all()

    # By-status breakdown
    status_counts: dict[str, int] = {}
    for o in all_orders:
        key = str(o.status.value if hasattr(o.status, "value") else o.status)
        status_counts[key] = status_counts.get(key, 0) + 1

    by_status = [
        {
            "status": k,
            "status_label": _ORDER_STATUS_LABELS.get(k, k),
            "count": v,
        }
        for k, v in status_counts.items()
    ]

    orders_list = []
    for o in all_orders:
        status_val = str(o.status.value if hasattr(o.status, "value") else o.status)
        works_total = sum(float(w.total or 0) for w in o.order_works)
        parts_total = sum(float(p.total or 0) for p in o.order_parts)

        vehicle_info: str | None = None
        customer_name: str | None = None
        if o.vehicle:
            brand_name = o.vehicle.brand.name if o.vehicle.brand else ""
            model_name = o.vehicle.model.name if o.vehicle.model else ""
            plate = o.vehicle.license_plate or ""
            vehicle_info = f"{brand_name} {model_name} {plate}".strip()
            if o.vehicle.customer:
                customer_name = o.vehicle.customer.full_name

        orders_list.append({
            "id": o.id,
            "number": o.number,
            "status": status_val,
            "status_label": _ORDER_STATUS_LABELS.get(status_val, status_val),
            "created_at": o.created_at.isoformat() if o.created_at else "",
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            "customer_name": customer_name,
            "vehicle_info": vehicle_info,
            "mechanic_name": o.mechanic.full_name if o.mechanic else None,
            "total_amount": float(o.total_amount or 0),
            "paid_amount": float(o.paid_amount or 0),
            "works_total": round(works_total, 2),
            "parts_total": round(parts_total, 2),
        })

    total_amount = sum(o["total_amount"] for o in orders_list)
    total_paid = sum(o["paid_amount"] for o in orders_list)

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_count": len(orders_list),
        "total_amount": round(total_amount, 2),
        "total_paid": round(total_paid, 2),
        "by_status": by_status,
        "orders": orders_list,
    }


def get_parts_report_data(
    db: Session,
    date_from: date,
    date_to: date,
) -> dict:
    """Parts usage statistics and low-stock alerts."""

    # Parts used in completed/paid orders
    rows = (
        db.query(
            Part.id.label("part_id"),
            Part.name.label("part_name"),
            Part.part_number.label("part_number"),
            Part.category.label("category"),
            Part.purchase_price_last.label("purchase_price_last"),
            func.sum(OrderPart.quantity).label("total_quantity"),
            func.sum(OrderPart.total).label("total_revenue"),
            func.count(func.distinct(OrderPart.order_id)).label("orders_count"),
        )
        .join(OrderPart, OrderPart.part_id == Part.id)
        .join(Order, Order.id == OrderPart.order_id)
        .filter(
            Order.status.in_(["paid", "completed"]),
            func.date(Order.created_at) >= date_from,
            func.date(Order.created_at) <= date_to,
        )
        .group_by(Part.id, Part.name, Part.part_number, Part.category, Part.purchase_price_last)
        .order_by(func.sum(OrderPart.total).desc())
        .all()
    )

    # Current stock levels
    warehouse_rows = db.query(WarehouseItem).options(joinedload(WarehouseItem.part)).all()
    stock_map: dict[int, float] = {w.part_id: float(w.quantity or 0) for w in warehouse_rows}
    min_map: dict[int, float] = {w.part_id: float(w.min_quantity or 0) for w in warehouse_rows}

    top_parts = []
    for r in rows:
        pid = r.part_id
        cat = r.category.value if hasattr(r.category, "value") else str(r.category)
        total_rev = round(float(r.total_revenue or 0), 2)
        total_qty = float(r.total_quantity or 0)
        purchase_price = float(r.purchase_price_last or 0)
        total_cost = round(purchase_price * total_qty, 2)
        total_margin = round(total_rev - total_cost, 2)
        margin_pct = round((total_margin / total_rev * 100) if total_rev else 0, 1)
        top_parts.append({
            "part_id": pid,
            "part_name": r.part_name,
            "part_number": r.part_number,
            "category": cat,
            "category_label": _PART_CATEGORY_LABELS.get(cat, cat),
            "total_quantity": total_qty,
            "total_revenue": total_rev,
            "total_cost": total_cost,
            "total_margin": total_margin,
            "margin_pct": margin_pct,
            "orders_count": int(r.orders_count or 0),
            "current_stock": stock_map.get(pid, 0),
        })

    total_parts_revenue = sum(p["total_revenue"] for p in top_parts)
    total_quantity_sold = sum(p["total_quantity"] for p in top_parts)
    total_parts_cost = round(sum(p["total_cost"] for p in top_parts), 2)
    total_parts_margin = round(total_parts_revenue - total_parts_cost, 2)
    total_margin_pct = round(
        (total_parts_margin / total_parts_revenue * 100) if total_parts_revenue else 0, 1
    )

    # Low-stock items (quantity <= min_quantity)
    low_stock_items = [
        w for w in warehouse_rows
        if float(w.quantity or 0) <= float(w.min_quantity or 0)
    ]
    low_stock_parts = []
    for w in low_stock_items:
        if not w.part:
            continue
        raw_cat = w.part.category
        cat = raw_cat.value if hasattr(raw_cat, "value") else (str(raw_cat) if raw_cat else "other")
        low_stock_parts.append({
            "part_id": w.part_id,
            "part_name": w.part.name,
            "part_number": w.part.part_number,
            "category": cat,
            "category_label": _PART_CATEGORY_LABELS.get(cat, cat),
            "total_quantity": 0,
            "total_revenue": 0,
            "orders_count": 0,
            "current_stock": float(w.quantity or 0),
        })

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_parts_revenue": round(total_parts_revenue, 2),
        "total_quantity_sold": round(total_quantity_sold, 2),
        "total_parts_cost": total_parts_cost,
        "total_parts_margin": total_parts_margin,
        "total_margin_pct": total_margin_pct,
        "top_parts": top_parts,
        "low_stock_parts": low_stock_parts,
    }
