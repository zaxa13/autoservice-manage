from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import Optional
from collections import defaultdict
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.models.appointment import Appointment
from app.models.appointment_post import AppointmentPost
from app.models.employee import Employee
from app.models.setting import Setting

router = APIRouter()

# ── Russian locale helpers ────────────────────────────────────────────────────

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


# ── Period bounds ─────────────────────────────────────────────────────────────

def _get_period_bounds(
    period: str,
    today: date,
    ref_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Returns (start, end, prev_start, prev_end, label, chart_mode)
    chart_mode: 'days' | 'weeks' | 'months'
    ref_date: опорная дата для навигации (какой месяц/год смотрим)
    """
    nav = ref_date or today  # опорная точка для навигации

    if period == "custom" and date_from and date_to:
        start, end = date_from, date_to
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
        start = end = nav
        prev_start = prev_end = nav - timedelta(days=1)
        label = f"{nav.day} {_MONTHS_RU_GEN[nav.month]} {nav.year}"
        chart_mode = "days"

    elif period == "week":
        dow = nav.weekday()
        start = nav - timedelta(days=dow)
        end = min(start + timedelta(days=6), today)
        prev_start = start - timedelta(days=7)
        prev_end = prev_start + timedelta(days=6)
        label = (
            f"{start.day} {_MONTHS_RU_GEN[start.month]}"
            f" – {end.day} {_MONTHS_RU_GEN[end.month]} {end.year}"
        )
        chart_mode = "days"

    elif period == "month":
        start = nav.replace(day=1)
        # Прошлый месяц — полный, если не текущий → полный; если текущий → до сегодня
        is_current = (nav.year == today.year and nav.month == today.month)
        end = today if is_current else date(nav.year, nav.month, monthrange(nav.year, nav.month)[1])
        prev_month_last = start - timedelta(days=1)
        prev_start = prev_month_last.replace(day=1)
        prev_end = prev_month_last  # полный прошлый месяц
        label = f"{_MONTHS_RU[nav.month]} {nav.year}"
        chart_mode = "days"

    elif period == "year":
        ref_year = nav.year
        start = date(ref_year, 1, 1)
        end = today if ref_year == today.year else date(ref_year, 12, 31)
        prev_start = date(ref_year - 1, 1, 1)
        prev_end = date(ref_year - 1, 12, 31)
        label = str(ref_year)
        chart_mode = "months"

    else:  # quarter
        q_month = ((nav.month - 1) // 3) * 3 + 1
        start = nav.replace(month=q_month, day=1)
        end = min(date(nav.year, q_month + 2, monthrange(nav.year, q_month + 2)[1])
                  if q_month <= 10 else date(nav.year, 12, 31), today)
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

    return start, end, prev_start, prev_end, label, chart_mode


# ── Revenue aggregation ───────────────────────────────────────────────────────

def _revenue_range(db: Session, start: date, end: date) -> float:
    return float(
        db.query(func.sum(Payment.amount)).filter(
            Payment.status == PaymentStatus.SUCCEEDED,
            func.date(Payment.created_at) >= start,
            func.date(Payment.created_at) <= end,
        ).scalar() or 0
    )


def _revenue_by_day(db: Session, start: date, end: date) -> dict:
    """Returns {date_str: amount}"""
    rows = db.query(
        func.date(Payment.created_at),
        func.sum(Payment.amount),
    ).filter(
        Payment.status == PaymentStatus.SUCCEEDED,
        func.date(Payment.created_at) >= start,
        func.date(Payment.created_at) <= end,
    ).group_by(func.date(Payment.created_at)).all()
    return {str(r[0]): float(r[1] or 0) for r in rows}


def _revenue_by_month(db: Session, year: int) -> dict:
    """Returns {'YYYY-MM': amount}"""
    rows = db.query(
        func.strftime('%Y-%m', Payment.created_at),
        func.sum(Payment.amount),
    ).filter(
        Payment.status == PaymentStatus.SUCCEEDED,
        func.strftime('%Y', Payment.created_at) == str(year),
    ).group_by(func.strftime('%Y-%m', Payment.created_at)).all()
    return {str(r[0]): float(r[1] or 0) for r in rows}


# ── Post load ────────────────────────────────────────────────────────────────

def _calc_load(db: Session, posts, target_date: date) -> int | None:
    if not posts:
        return None
    total_slots = sum(
        len(p.slot_times) if p.slot_times else p.max_slots
        for p in posts
    )
    if not total_slots:
        return None
    filled = db.query(func.count(Appointment.id)).filter(
        Appointment.date == target_date,
        Appointment.status.notin_(["no_show", "cancelled"]),
    ).scalar() or 0
    return round(min(filled / total_slots * 100, 100))


# ── Percent change ────────────────────────────────────────────────────────────

def _pct(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.get("/stats")
def get_dashboard_stats(
    period: str = Query("month", regex="^(day|week|month|year|quarter|custom)$"),
    ref_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if period == "custom":
        if not date_from or not date_to:
            raise HTTPException(400, "date_from и date_to обязательны для периода custom")
        if date_from > date_to:
            raise HTTPException(400, "date_from не может быть позже date_to")
        if (date_to - date_from).days > 366:
            raise HTTPException(400, "Период не может превышать 366 дней")

    today = date.today()
    tomorrow = today + timedelta(days=1)
    now = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # ref_date не может быть в будущем
    if ref_date and ref_date > today:
        ref_date = today

    start, end, prev_start, prev_end, period_label, chart_mode = _get_period_bounds(
        period, today, ref_date, date_from, date_to
    )

    # ── 1. Revenue (period) ──────────────────────────────────────────────────
    rev_current = _revenue_range(db, start, end)
    rev_prev = _revenue_range(db, prev_start, prev_end)

    # Monthly plan from settings — берём по месяцу начала просматриваемого периода
    plan_key = f"revenue_plan_{start.year}_{start.month:02d}"
    setting_row = db.query(Setting).filter(Setting.key == plan_key).first()
    revenue_plan = float(setting_row.value) if setting_row and setting_row.value else None
    plan_pct = round(rev_current / revenue_plan * 100, 1) if revenue_plan else None

    # ── 2. Avg check (period) ────────────────────────────────────────────────
    def _avg_check_range(s: date, e: date):
        q = db.query(func.count(Order.id), func.sum(Order.total_amount)).filter(
            Order.status.in_(["paid", "completed"]),
            func.date(Order.created_at) >= s,
            func.date(Order.created_at) <= e,
        ).one()
        cnt, total = q
        return (float(total or 0) / cnt) if cnt else 0, cnt or 0

    avg_check, orders_count = _avg_check_range(start, end)
    avg_check_prev, orders_count_prev = _avg_check_range(prev_start, prev_end)

    # ── 3. WIP amount ────────────────────────────────────────────────────────
    wip_rows = db.query(Order.total_amount).filter(
        Order.status == "in_progress"
    ).all()
    wip_amount = sum(float(r[0] or 0) for r in wip_rows)

    # ── 4. Post load ─────────────────────────────────────────────────────────
    posts = db.query(AppointmentPost).all()
    load_today = _calc_load(db, posts, today)
    load_tomorrow = _calc_load(db, posts, tomorrow)

    # ── 5. Pipeline 7 days ───────────────────────────────────────────────────
    pipeline_7d = []
    for i in range(7):
        d = today + timedelta(days=i)
        appts = db.query(func.count(Appointment.id)).filter(
            Appointment.date == d,
            Appointment.status.notin_(["no_show", "cancelled"]),
        ).scalar() or 0
        load = _calc_load(db, posts, d)
        pipeline_7d.append({
            "date": d.isoformat(),
            "day_name": _weekday_short(d),
            "day_label": _day_label(d),
            "appointments_count": appts,
            "load_pct": load,
            "is_today": d == today,
        })

    # ── 6. Alerts ────────────────────────────────────────────────────────────
    unpaid = db.query(Order).filter(
        Order.status == "ready_for_payment",
        func.date(Order.created_at) <= yesterday,
    ).all()
    unpaid_sum = sum(max(float(o.total_amount) - float(o.paid_amount), 0) for o in unpaid)

    stuck_raw = db.query(Order).options(joinedload(Order.mechanic)).filter(
        Order.status == "in_progress",
        Order.created_at <= two_days_ago,
    ).all()
    stuck_orders = []
    for o in stuck_raw:
        try:
            created = o.created_at.replace(tzinfo=None) if o.created_at.tzinfo else o.created_at
            days = max(int((now - created).total_seconds() / 86400), 1)
        except Exception:
            days = 2
        stuck_orders.append({
            "id": o.id,
            "number": o.number,
            "mechanic_name": o.mechanic.full_name if o.mechanic else None,
            "days_in_work": days,
        })

    without_mechanic = db.query(func.count(Order.id)).filter(
        Order.status.in_(["new", "estimation", "in_progress"]),
        Order.mechanic_id == None,
    ).scalar() or 0

    total_today_appts = db.query(func.count(Appointment.id)).filter(
        Appointment.date == today,
    ).scalar() or 0
    no_shows = db.query(func.count(Appointment.id)).filter(
        Appointment.date == today,
        Appointment.status == "no_show",
    ).scalar() or 0
    no_shows_pct = round(no_shows / total_today_appts * 100) if total_today_appts else 0

    # ── 7. Mechanics stats (period) ──────────────────────────────────────────
    period_orders = db.query(Order).filter(
        Order.mechanic_id != None,
        Order.status.in_(["in_progress", "ready_for_payment", "paid", "completed"]),
        func.date(Order.created_at) >= start,
        func.date(Order.created_at) <= end,
    ).all()

    by_mechanic: dict = defaultdict(list)
    for o in period_orders:
        by_mechanic[o.mechanic_id].append(o)

    # Also include mechanics currently in_progress (may have 0 in period)
    active_now = db.query(Order.mechanic_id).filter(
        Order.mechanic_id != None,
        Order.status == "in_progress",
    ).all()
    mechanic_ids = set(by_mechanic.keys()) | {mid for (mid,) in active_now}

    # Team avg check (all mechanics, period)
    team_total_rev = sum(float(o.total_amount) for o in period_orders)
    team_total_cnt = len(period_orders)
    team_avg_check = team_total_rev / team_total_cnt if team_total_cnt else 0

    mechanics_stats = []
    if mechanic_ids:
        emps = db.query(Employee).filter(Employee.id.in_(mechanic_ids)).all()
        emp_map = {e.id: e for e in emps}
        for mid in mechanic_ids:
            emp = emp_map.get(mid)
            if not emp:
                continue
            orders = by_mechanic.get(mid, [])
            mech_rev = sum(float(o.total_amount) for o in orders)
            mech_cnt = len(orders)
            mech_avg = mech_rev / mech_cnt if mech_cnt else 0
            vs_team = _pct(mech_avg, team_avg_check) if team_avg_check else None
            mechanics_stats.append({
                "id": mid,
                "name": emp.full_name,
                "orders_count": mech_cnt,
                "revenue": round(mech_rev),
                "avg_check": round(mech_avg),
                "vs_team_pct": vs_team,
            })
        mechanics_stats.sort(key=lambda x: x["revenue"], reverse=True)

    # ── 8. Revenue chart ─────────────────────────────────────────────────────
    revenue_chart = []

    if chart_mode == "months":
        # Годовой вид: 12 месяцев текущего года vs тот же месяц прошлого года
        ref_year = start.year
        cur_by_month = _revenue_by_month(db, ref_year)
        prev_by_month = _revenue_by_month(db, ref_year - 1)
        for m in range(1, 13):
            key = f"{ref_year}-{m:02d}"
            prev_key = f"{ref_year - 1}-{m:02d}"
            m_start = date(ref_year, m, 1)
            is_future = m_start > today
            revenue_chart.append({
                "label": _MONTHS_RU[m][:3],  # Янв, Фев, ...
                "date": m_start.isoformat(),
                "current": cur_by_month.get(key, 0),
                "previous": prev_by_month.get(prev_key, 0),
                "is_today": (m == today.month and ref_year == today.year),
                "is_future": is_future,
            })

    elif chart_mode == "days":
        cur_by_day = _revenue_by_day(db, start, end)
        prev_by_day = _revenue_by_day(db, prev_start, prev_end)
        delta = (end - start).days
        prev_delta = (prev_end - prev_start).days
        for i in range(delta + 1):
            d_cur = start + timedelta(days=i)
            d_prev = prev_start + timedelta(days=min(i, prev_delta))
            revenue_chart.append({
                "label": _day_label(d_cur),
                "date": d_cur.isoformat(),
                "current": cur_by_day.get(d_cur.isoformat(), 0),
                "previous": prev_by_day.get(d_prev.isoformat(), 0),
                "is_today": d_cur == today,
                "is_future": False,
            })

    else:  # weeks
        cur_by_day = _revenue_by_day(db, start, end)
        prev_by_day = _revenue_by_day(db, prev_start, prev_end)
        week_offset = 0
        d = start
        while d <= end:
            week_end = min(d + timedelta(days=6), end)
            cur_sum = sum(
                cur_by_day.get((d + timedelta(days=j)).isoformat(), 0)
                for j in range((week_end - d).days + 1)
            )
            p_start_w = prev_start + timedelta(weeks=week_offset)
            p_end_w = min(p_start_w + timedelta(days=6), prev_end)
            prev_sum = sum(
                prev_by_day.get((p_start_w + timedelta(days=j)).isoformat(), 0)
                for j in range((p_end_w - p_start_w).days + 1)
            )
            revenue_chart.append({
                "label": f"Нед {week_offset + 1}",
                "date": d.isoformat(),
                "current": cur_sum,
                "previous": prev_sum,
                "is_today": d <= today <= week_end,
                "is_future": False,
            })
            d = week_end + timedelta(days=1)
            week_offset += 1

    # Навигационные подсказки для фронтенда
    nav_ref = (ref_date or today).isoformat()
    can_go_next = end < today  # можно идти вперёд если ещё не дошли до сегодня

    return {
        "period": period,
        "period_label": period_label,
        "nav_ref": nav_ref,
        "can_go_next": can_go_next,
        "revenue": {
            "value": round(rev_current),
            "prev_value": round(rev_prev),
            "change_pct": _pct(rev_current, rev_prev),
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
            "unpaid_orders_count": len(unpaid),
            "unpaid_orders_sum": round(unpaid_sum),
            "stuck_orders": stuck_orders,
            "orders_without_mechanic_count": without_mechanic,
            "no_shows_today": no_shows,
            "no_shows_pct": no_shows_pct,
        },
    }
