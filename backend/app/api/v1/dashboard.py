"""Дашборд — сводная статистика автосервиса.

Один эндпоинт `/stats` с метриками за период (day/week/month/quarter/
year/custom). Все агрегации идут под RLS, фильтрация по тенанту
автоматическая.

Period bounds — пуре-Python helper (без БД). Aggregations — async через
`select(func.sum(...))`. `func.strftime` (SQLite) заменён на Postgres
`to_char(date, 'YYYY-MM')`.
"""
from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantClaims
from app.dependencies import get_current_claims, get_tenant_db
from app.models.appointment import Appointment
from app.models.appointment_post import AppointmentPost
from app.models.employee import Employee
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.models.setting import Setting
from app.schemas.responses import DashboardStatsResponse, ErrorResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Russian locale helpers
# ---------------------------------------------------------------------------
_MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
_MONTHS_RU_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
_WEEKDAYS_SHORT_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _day_label(d: date) -> str:
    return f"{d.day} {_MONTHS_RU_GEN[d.month]}"


def _weekday_short(d: date) -> str:
    return _WEEKDAYS_SHORT_RU[d.weekday()]


# ---------------------------------------------------------------------------
# Period bounds (pure-Python)
# ---------------------------------------------------------------------------
def _get_period_bounds(
    period: str,
    today: date,
    ref_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Return (start, end, full_end, prev_start, prev_end, label, chart_mode).

    `end` — фактический конец данных (для текущего периода обрезан до сегодня).
    `full_end` — астрономический конец периода (последний день месяца/квартала/года),
    нужен для линейного прогноза и определения «текущности» периода.
    """
    nav = ref_date or today

    if period == "custom" and date_from and date_to:
        start, end = date_from, date_to
        full_end = end
        span = (end - start).days + 1
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        s_label = f"{start.day} {_MONTHS_RU_GEN[start.month]}"
        e_label = f"{end.day} {_MONTHS_RU_GEN[end.month]}"
        if start.year != end.year:
            s_label += f" {start.year}"
        label = f"{s_label} – {e_label} {end.year}"
        chart_mode = "days" if span <= 90 else "weeks"

    elif period == "day":
        start = end = full_end = nav
        prev_start = prev_end = nav - timedelta(days=1)
        label = f"{nav.day} {_MONTHS_RU_GEN[nav.month]} {nav.year}"
        chart_mode = "days"

    elif period == "week":
        dow = nav.weekday()
        start = nav - timedelta(days=dow)
        full_end = start + timedelta(days=6)
        end = min(full_end, today)
        prev_start = start - timedelta(days=7)
        prev_end = prev_start + timedelta(days=6)
        label = (
            f"{start.day} {_MONTHS_RU_GEN[start.month]}"
            f" – {end.day} {_MONTHS_RU_GEN[end.month]} {end.year}"
        )
        chart_mode = "days"

    elif period == "month":
        start = nav.replace(day=1)
        full_end = date(nav.year, nav.month, monthrange(nav.year, nav.month)[1])
        is_current = (nav.year == today.year and nav.month == today.month)
        end = today if is_current else full_end
        prev_month_last = start - timedelta(days=1)
        prev_start = prev_month_last.replace(day=1)
        prev_end = prev_month_last
        label = f"{_MONTHS_RU[nav.month]} {nav.year}"
        chart_mode = "days"

    elif period == "year":
        ref_year = nav.year
        start = date(ref_year, 1, 1)
        full_end = date(ref_year, 12, 31)
        end = today if ref_year == today.year else full_end
        prev_start = date(ref_year - 1, 1, 1)
        prev_end = date(ref_year - 1, 12, 31)
        label = str(ref_year)
        chart_mode = "months"

    else:  # quarter
        q_month = ((nav.month - 1) // 3) * 3 + 1
        start = nav.replace(month=q_month, day=1)
        q_end_month = q_month + 2 if q_month <= 10 else 12
        q_end_day = monthrange(nav.year, q_end_month)[1]
        full_end = date(nav.year, q_end_month, q_end_day)
        end = min(full_end, today)
        days_elapsed = (end - start).days
        if q_month > 3:
            prev_q_start = start.replace(month=q_month - 3)
        else:
            prev_q_start = start.replace(year=start.year - 1, month=q_month + 9)
        prev_start = prev_q_start
        prev_end = prev_q_start + timedelta(days=days_elapsed)
        q_num = (nav.month - 1) // 3 + 1
        label = f"Q{q_num} {nav.year}"
        chart_mode = "weeks"

    return start, end, full_end, prev_start, prev_end, label, chart_mode


def _pct(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
async def _revenue_range(db: AsyncSession, start: date, end: date) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.status == PaymentStatus.SUCCEEDED.value,
            func.date(Payment.created_at) >= start,
            func.date(Payment.created_at) <= end,
        )
    )
    return float(result.scalar() or 0)


async def _revenue_by_day(db: AsyncSession, start: date, end: date) -> dict[str, float]:
    rows = (
        await db.execute(
            select(
                func.date(Payment.created_at).label("d"),
                func.sum(Payment.amount),
            ).where(
                Payment.status == PaymentStatus.SUCCEEDED.value,
                func.date(Payment.created_at) >= start,
                func.date(Payment.created_at) <= end,
            ).group_by(func.date(Payment.created_at))
        )
    ).all()
    return {str(r[0]): float(r[1] or 0) for r in rows}


async def _revenue_by_month(db: AsyncSession, year: int) -> dict[str, float]:
    """Postgres-aware: to_char(created_at, 'YYYY-MM')."""
    fmt = func.to_char(Payment.created_at, "YYYY-MM")
    rows = (
        await db.execute(
            select(fmt.label("m"), func.sum(Payment.amount))
            .where(
                Payment.status == PaymentStatus.SUCCEEDED.value,
                func.extract("year", Payment.created_at) == year,
            )
            .group_by(fmt)
        )
    ).all()
    return {str(r[0]): float(r[1] or 0) for r in rows}


async def _avg_check_range(db: AsyncSession, s: date, e: date) -> tuple[float, int]:
    row = (
        await db.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            ).where(
                Order.status.in_(["paid", "completed"]),
                func.date(Order.created_at) >= s,
                func.date(Order.created_at) <= e,
            )
        )
    ).one()
    cnt = int(row[0] or 0)
    total = float(row[1] or 0)
    return (total / cnt) if cnt else 0.0, cnt


async def _calc_post_load(
    db: AsyncSession, posts: list[AppointmentPost], target: date
) -> Optional[int]:
    if not posts:
        return None
    total_slots = sum(
        len(p.slot_times) if p.slot_times else p.max_slots
        for p in posts
    )
    if not total_slots:
        return None
    filled = (
        await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.date == target,
                Appointment.status.notin_(["no_show", "cancelled"]),
            )
        )
    ).scalar() or 0
    return round(min(filled / total_slots * 100, 100))


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------
@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Статистика дашборда",
    responses={
        401: {"model": ErrorResponse, "description": "Не авторизован"},
        400: {"model": ErrorResponse, "description": "Некорректные параметры периода"},
    },
)
async def get_dashboard_stats(
    period: str = Query("month", pattern="^(day|week|month|year|quarter|custom)$"),
    ref_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    if period == "custom":
        if not date_from or not date_to:
            raise HTTPException(400, "date_from и date_to обязательны для custom")
        if date_from > date_to:
            raise HTTPException(400, "date_from не может быть позже date_to")
        if (date_to - date_from).days > 366:
            raise HTTPException(400, "Период не может превышать 366 дней")

    today = date.today()
    tomorrow = today + timedelta(days=1)
    now = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    if ref_date and ref_date > today:
        ref_date = today

    start, end, full_end, prev_start, prev_end, period_label, chart_mode = _get_period_bounds(
        period, today, ref_date, date_from, date_to
    )

    # 1. Revenue.
    rev_current = await _revenue_range(db, start, end)
    rev_prev = await _revenue_range(db, prev_start, prev_end)
    plan_key = f"revenue_plan_{start.year}_{start.month:02d}"
    setting_row = await db.get(Setting, (claims.tenant_id, plan_key))
    revenue_plan = float(setting_row.value) if setting_row and setting_row.value else None
    plan_pct = round(rev_current / revenue_plan * 100, 1) if revenue_plan else None

    # Линейный прогноз: для текущего (незавершённого) периода — факт * всего_дней / прошло_дней.
    # Для закрытого периода прогноз == факт; для будущего — null.
    rev_forecast: Optional[float] = None
    if start <= today <= full_end:
        days_elapsed = (end - start).days + 1
        total_days = (full_end - start).days + 1
        if days_elapsed > 0 and total_days > days_elapsed:
            rev_forecast = round(rev_current / days_elapsed * total_days)
        else:
            rev_forecast = round(rev_current)
    elif full_end < today:
        rev_forecast = round(rev_current)

    # 2. Avg check.
    avg_check, orders_count = await _avg_check_range(db, start, end)
    avg_check_prev, orders_count_prev = await _avg_check_range(db, prev_start, prev_end)

    # 3. WIP.
    wip_amount = float((
        await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0))
            .where(Order.status == "in_progress")
        )
    ).scalar() or 0)

    # 4. Post load.
    posts = list(
        (await db.execute(select(AppointmentPost))).scalars().all()
    )
    load_today = await _calc_post_load(db, posts, today)
    load_tomorrow = await _calc_post_load(db, posts, tomorrow)

    # 5. Pipeline 7d.
    pipeline_7d = []
    for i in range(7):
        d = today + timedelta(days=i)
        appts = (
            await db.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.date == d,
                    Appointment.status.notin_(["no_show", "cancelled"]),
                )
            )
        ).scalar() or 0
        load = await _calc_post_load(db, posts, d)
        pipeline_7d.append({
            "date": d.isoformat(), "day_name": _weekday_short(d),
            "day_label": _day_label(d), "appointments_count": int(appts),
            "load_pct": load, "is_today": d == today,
        })

    # 6. Alerts.
    unpaid_rows = (
        await db.execute(
            select(Order).where(
                Order.status == "ready_for_payment",
                func.date(Order.created_at) <= yesterday,
            )
        )
    ).scalars().all()
    unpaid_sum = sum(
        max(float(o.total_amount or 0) - float(o.paid_amount or 0), 0)
        for o in unpaid_rows
    )

    stuck_raw = (
        await db.execute(
            select(Order).where(
                Order.status == "in_progress",
                Order.created_at <= two_days_ago,
            )
        )
    ).scalars().all()
    mechanics = {}
    if stuck_raw:
        mech_ids = {o.mechanic_id for o in stuck_raw if o.mechanic_id}
        if mech_ids:
            mechanics = {
                e.id: e
                for e in (
                    await db.execute(select(Employee).where(Employee.id.in_(mech_ids)))
                ).scalars()
            }
    stuck_orders = []
    for o in stuck_raw:
        try:
            created = o.created_at if o.created_at.tzinfo else o.created_at.replace(tzinfo=timezone.utc)
            days = max(int((now - created).total_seconds() / 86400), 1)
        except Exception:
            days = 2
        mech = mechanics.get(o.mechanic_id) if o.mechanic_id else None
        stuck_orders.append({
            "id": o.id, "number": o.number,
            "mechanic_name": mech.full_name if mech else None,
            "days_in_work": days,
        })

    without_mechanic = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.status.in_(["new", "estimation", "in_progress"]),
                Order.mechanic_id.is_(None),
            )
        )
    ).scalar() or 0

    total_today_appts = (
        await db.execute(
            select(func.count(Appointment.id)).where(Appointment.date == today)
        )
    ).scalar() or 0
    no_shows = (
        await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.date == today, Appointment.status == "no_show"
            )
        )
    ).scalar() or 0
    no_shows_pct = round(no_shows / total_today_appts * 100) if total_today_appts else 0

    # 7. Mechanics stats.
    period_orders = (
        await db.execute(
            select(Order).where(
                Order.mechanic_id.is_not(None),
                Order.status.in_(["in_progress", "ready_for_payment", "paid", "completed"]),
                func.date(Order.created_at) >= start,
                func.date(Order.created_at) <= end,
            )
        )
    ).scalars().all()
    by_mechanic: dict[int, list] = defaultdict(list)
    for o in period_orders:
        by_mechanic[o.mechanic_id].append(o)
    active_now_ids = (
        await db.execute(
            select(Order.mechanic_id).where(
                Order.mechanic_id.is_not(None),
                Order.status == "in_progress",
            ).distinct()
        )
    ).scalars().all()
    mechanic_ids = set(by_mechanic.keys()) | set(active_now_ids)

    team_total_rev = sum(float(o.total_amount or 0) for o in period_orders)
    team_total_cnt = len(period_orders)
    team_avg_check = team_total_rev / team_total_cnt if team_total_cnt else 0

    mechanics_stats = []
    if mechanic_ids:
        emps_rows = (
            await db.execute(select(Employee).where(Employee.id.in_(mechanic_ids)))
        ).scalars().all()
        emp_map = {e.id: e for e in emps_rows}
        for mid in mechanic_ids:
            emp = emp_map.get(mid)
            if not emp:
                continue
            orders = by_mechanic.get(mid, [])
            mech_rev = sum(float(o.total_amount or 0) for o in orders)
            mech_cnt = len(orders)
            mech_avg = mech_rev / mech_cnt if mech_cnt else 0
            vs_team = _pct(mech_avg, team_avg_check) if team_avg_check else None
            mechanics_stats.append({
                "id": mid, "name": emp.full_name,
                "orders_count": mech_cnt, "revenue": round(mech_rev),
                "avg_check": round(mech_avg), "vs_team_pct": vs_team,
            })
        mechanics_stats.sort(key=lambda x: x["revenue"], reverse=True)

    # 8. Revenue chart.
    revenue_chart = []
    if chart_mode == "months":
        ref_year = start.year
        cur_by_m = await _revenue_by_month(db, ref_year)
        prev_by_m = await _revenue_by_month(db, ref_year - 1)
        for m in range(1, 13):
            key = f"{ref_year}-{m:02d}"
            pkey = f"{ref_year - 1}-{m:02d}"
            m_start = date(ref_year, m, 1)
            revenue_chart.append({
                "label": _MONTHS_RU[m][:3], "date": m_start.isoformat(),
                "current": cur_by_m.get(key, 0), "previous": prev_by_m.get(pkey, 0),
                "is_today": (m == today.month and ref_year == today.year),
                "is_future": m_start > today,
            })
    elif chart_mode == "days":
        cur_by_d = await _revenue_by_day(db, start, end)
        prev_by_d = await _revenue_by_day(db, prev_start, prev_end)
        delta = (end - start).days
        prev_delta = (prev_end - prev_start).days
        for i in range(delta + 1):
            d_cur = start + timedelta(days=i)
            d_prev = prev_start + timedelta(days=min(i, prev_delta))
            revenue_chart.append({
                "label": _day_label(d_cur), "date": d_cur.isoformat(),
                "current": cur_by_d.get(d_cur.isoformat(), 0),
                "previous": prev_by_d.get(d_prev.isoformat(), 0),
                "is_today": d_cur == today, "is_future": False,
            })
    else:  # weeks
        cur_by_d = await _revenue_by_day(db, start, end)
        prev_by_d = await _revenue_by_day(db, prev_start, prev_end)
        wo = 0
        d = start
        while d <= end:
            week_end = min(d + timedelta(days=6), end)
            cur_sum = sum(
                cur_by_d.get((d + timedelta(days=j)).isoformat(), 0)
                for j in range((week_end - d).days + 1)
            )
            p_start_w = prev_start + timedelta(weeks=wo)
            p_end_w = min(p_start_w + timedelta(days=6), prev_end)
            prev_sum = sum(
                prev_by_d.get((p_start_w + timedelta(days=j)).isoformat(), 0)
                for j in range((p_end_w - p_start_w).days + 1)
            )
            revenue_chart.append({
                "label": f"Нед {wo + 1}", "date": d.isoformat(),
                "current": cur_sum, "previous": prev_sum,
                "is_today": d <= today <= week_end, "is_future": False,
            })
            d = week_end + timedelta(days=1)
            wo += 1

    nav_ref = (ref_date or today).isoformat()
    can_go_next = end < today

    return {
        "period": period,
        "period_label": period_label,
        "nav_ref": nav_ref,
        "can_go_next": can_go_next,
        "revenue": {
            "value": round(rev_current),
            "prev_value": round(rev_prev),
            "change_pct": _pct(rev_current, rev_prev),
            "forecast": rev_forecast,
            "plan": revenue_plan,
            "plan_pct": plan_pct,
        },
        "avg_check": {
            "value": round(avg_check),
            "prev_value": round(avg_check_prev),
            "change_pct": _pct(avg_check, avg_check_prev),
        },
        "orders_count": {
            "value": orders_count,
            "prev_value": orders_count_prev,
            "change_pct": _pct(orders_count, orders_count_prev),
        },
        "wip_amount": round(wip_amount),
        "post_load_today_pct": load_today,
        "post_load_tomorrow_pct": load_tomorrow,
        "pipeline_7d": pipeline_7d,
        "revenue_chart": revenue_chart,
        "mechanics_stats": mechanics_stats,
        "alerts": {
            "unpaid_orders_count": len(unpaid_rows),
            "unpaid_orders_sum": round(unpaid_sum),
            "stuck_orders": stuck_orders,
            "orders_without_mechanic_count": int(without_mechanic),
            "no_shows_today": int(no_shows),
            "no_shows_pct": int(no_shows_pct),
        },
    }
