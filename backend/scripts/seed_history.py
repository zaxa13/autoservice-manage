"""
Скрипт наполнения исторических данных с января по март 2026.
Использует уже существующих клиентов, автомобили, работы и запчасти.
Добавляет мастеров и ~90 заказов с платежами для наглядной статистики.

Запуск: из директории backend/
    python scripts/seed_history.py
"""

import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from datetime import datetime, date, timedelta
from decimal import Decimal

db = SessionLocal()
random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# 0. Проверяем существующие данные
# ─────────────────────────────────────────────────────────────────────────────
vehicles    = db.execute(text("SELECT id, customer_id FROM vehicles")).fetchall()
works       = db.execute(text("SELECT id, price FROM works")).fetchall()
parts       = db.execute(text("SELECT id, price FROM parts WHERE id <= 20")).fetchall()
max_order   = db.execute(text("SELECT COALESCE(MAX(id),0) FROM orders")).scalar()
max_payment = db.execute(text("SELECT COALESCE(MAX(id),0) FROM payments")).scalar()

print(f"Авто: {len(vehicles)}, работ: {len(works)}, запчастей: {len(parts)}")
print(f"Уже заказов: {max_order}, платежей: {max_payment}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Добавляем мастеров (если ещё нет)
# ─────────────────────────────────────────────────────────────────────────────
existing_mechs = db.execute(text("SELECT id, full_name FROM employees WHERE position='mechanic'")).fetchall()
if not existing_mechs:
    print("\n→ Добавляем мастеров...")
    mechs_data = [
        ("Иванов Сергей Петрович",    "mechanic", "+79161110001", "2024-03-01", 60000),
        ("Климов Андрей Викторович",  "mechanic", "+79161110002", "2023-07-15", 65000),
        ("Зайцев Николай Олегович",   "mechanic", "+79161110003", "2025-01-10", 55000),
    ]
    mech_ids = []
    for name, pos, phone, hire_date, salary in mechs_data:
        r = db.execute(text("""
            INSERT INTO employees (full_name, position, phone, hire_date, salary_base, is_active)
            VALUES (:name, :pos, :phone, :hire_date, :salary, 1)
        """), {"name": name, "pos": pos, "phone": phone, "hire_date": hire_date, "salary": salary})
        mech_ids.append(r.lastrowid)
    db.commit()
    print(f"  Добавлено мастеров: {len(mech_ids)}, ID: {mech_ids}")
else:
    mech_ids = [m[0] for m in existing_mechs]
    print(f"\n→ Мастера уже есть: {[m[1] for m in existing_mechs]}")

# Кто принимает заказы (admin = id 1)
admin_id = db.execute(text("SELECT id FROM employees LIMIT 1")).scalar()

# ─────────────────────────────────────────────────────────────────────────────
# 2. Генерируем заказы по месяцам с реалистичной динамикой
# ─────────────────────────────────────────────────────────────────────────────

# Сценарии заказов: (работы[], запчасти[], описание)
SCENARIOS = [
    # ТО
    {"works": [1,2,3], "parts": [1,3,4,6], "desc": "Плановое ТО: замена масла, фильтров"},
    {"works": [1,9],   "parts": [1,6],     "desc": "Замена масла + балансировка колёс"},
    {"works": [1,2,8], "parts": [1,3,6],   "desc": "ТО + развал-схождение"},
    {"works": [5,6],   "parts": [8,9],     "desc": "Замена антифриза и тормозной жидкости"},
    {"works": [4,11],  "parts": [5],       "desc": "Замена топливного фильтра, промывка топливной системы"},
    # Тормоза
    {"works": [15,26,27], "parts": [11,12,9], "desc": "Диагностика и замена тормозных колодок"},
    {"works": [28],       "parts": [13,11],   "desc": "Замена тормозных дисков передних"},
    {"works": [15,28,27], "parts": [13,14,11,12], "desc": "Полная замена тормозной системы"},
    # Подвеска
    {"works": [14,30],  "parts": [24,25,26], "desc": "Диагностика подвески, замена амортизаторов передних"},
    {"works": [14,31],  "parts": [25,26],    "desc": "Замена амортизаторов задних"},
    {"works": [14,32,8],"parts": [27],       "desc": "Замена шаровых опор + развал-схождение"},
    {"works": [33,34,8],"parts": [28,29],    "desc": "Замена наконечников рулевых тяг, стоек стабилизатора"},
    {"works": [35],     "parts": [30],       "desc": "Замена ступичного подшипника"},
    # ГРМ / двигатель
    {"works": [13,18],  "parts": [16,17,18,19], "desc": "Диагностика + замена ремня ГРМ"},
    {"works": [21],     "parts": [21],       "desc": "Замена свечей зажигания"},
    {"works": [13,24,25],"parts": [34,32],   "desc": "Диагностика, замена катушки и лямбда-зонда"},
    {"works": [20],     "parts": [19,16],    "desc": "Замена помпы водяного насоса"},
    # Электрика
    {"works": [16,36],  "parts": [31],       "desc": "Диагностика электрики, замена аккумулятора"},
    {"works": [13,16],  "parts": [],         "desc": "Компьютерная диагностика двигателя и электрики"},
    # Только диагностика
    {"works": [13],     "parts": [],         "desc": "Компьютерная диагностика двигателя"},
    {"works": [14,17],  "parts": [],         "desc": "Диагностика ходовой части и подвески"},
    # Полировка
    {"works": [38],     "parts": [],         "desc": "Полировка кузова"},
]

# Распределение заказов по неделям (растём от января к марту)
# Январь: ~25 заказов, Февраль: ~35 заказов, Март 1-15: ~15 заказов

def workdays_in_range(start: date, end: date):
    """Рабочие дни (Пн-Сб) в диапазоне."""
    days = []
    d = start
    while d <= end:
        if d.weekday() < 6:  # Пн-Сб
            days.append(d)
        d += timedelta(days=1)
    return days

jan_days  = workdays_in_range(date(2026,1,5), date(2026,1,31))  # без новогодних
feb_days  = workdays_in_range(date(2026,2,1), date(2026,2,28))
mar_days  = workdays_in_range(date(2026,3,1), date(2026,3,15))

def pick_days(days_pool, count):
    return sorted(random.choices(days_pool, k=count))

jan_order_days  = pick_days(jan_days, 26)
feb_order_days  = pick_days(feb_days, 35)
mar_order_days  = pick_days(mar_days, 15)

all_order_days = jan_order_days + feb_order_days + mar_order_days

print(f"\n→ Будет создано заказов: {len(all_order_days)}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Создаём заказы
# ─────────────────────────────────────────────────────────────────────────────

vehicle_list = [v[0] for v in vehicles]
works_map    = {w[0]: float(w[1]) for w in works}
parts_map    = {p[0]: float(p[1]) for p in parts}

print("→ Создаём заказы и платежи...")

order_counter = max_order
created_orders = 0
created_payments = 0

# Сделаем февральские заказы "прошлого периода" — они уже есть в БД (orders 1-36)
# Мы создаём новые: январь 2026, + дополняем февраль и март свежими данными

for i, order_date in enumerate(all_order_days):
    order_counter += 1
    vehicle_id = random.choice(vehicle_list)
    mechanic_id = random.choice(mech_ids)
    scenario = random.choice(SCENARIOS)

    # Номер заказа
    order_num = f"ORD-2026-{order_counter:04d}"

    # Определяем статус: старые — completed, свежие — разные
    days_ago = (date(2026, 3, 15) - order_date).days
    if days_ago > 14:
        status = "completed"
    elif days_ago > 7:
        status = random.choices(["completed", "paid", "ready_for_payment"], weights=[70, 20, 10])[0]
    else:
        status = random.choices(["completed", "in_progress", "ready_for_payment", "new"], weights=[50, 20, 20, 10])[0]

    # Время создания: рабочие часы
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    created_at = datetime(order_date.year, order_date.month, order_date.day, hour, minute)

    # Вставляем заказ
    db.execute(text("""
        INSERT INTO orders (number, vehicle_id, employee_id, mechanic_id, status, 
                           total_amount, paid_amount, created_at)
        VALUES (:num, :vid, :eid, :mid, :status, 0, 0, :cat)
    """), {
        "num": order_num, "vid": vehicle_id, "eid": admin_id, "mid": mechanic_id,
        "status": status, "cat": created_at.isoformat()
    })
    order_id = db.execute(text("SELECT last_insert_rowid()")).scalar()

    # Работы из сценария
    total = 0.0
    for work_id in scenario["works"]:
        if work_id not in works_map:
            continue
        price = works_map[work_id]
        # Небольшая вариация цены ±10%
        price = round(price * random.uniform(0.95, 1.10) / 50) * 50
        qty = 1
        row_total = price * qty
        total += row_total
        db.execute(text("""
            INSERT INTO order_works (order_id, work_id, quantity, price, discount, total)
            VALUES (:oid, :wid, :qty, :price, 0, :total)
        """), {"oid": order_id, "wid": work_id, "qty": qty, "price": price, "total": row_total})

    # Запчасти из сценария
    for part_id in scenario["parts"]:
        if part_id not in parts_map:
            continue
        price = parts_map[part_id]
        price = round(price * random.uniform(0.98, 1.05) / 10) * 10
        qty = 1
        row_total = price * qty
        total += row_total
        db.execute(text("""
            INSERT INTO order_parts (order_id, part_id, quantity, price, discount, total)
            VALUES (:oid, :pid, :qty, :price, 0, :total)
        """), {"oid": order_id, "pid": part_id, "qty": qty, "price": price, "total": row_total})

    total = round(total, 2)

    # Обновляем total_amount
    db.execute(text("UPDATE orders SET total_amount=:t WHERE id=:id"),
               {"t": total, "id": order_id})

    # Платёж для завершённых/оплаченных
    paid_amount = 0.0
    if status in ("completed", "paid"):
        method = random.choices(["cash", "card"], weights=[55, 45])[0]
        # Платёж чуть позже создания заказа (в тот же день или +1-2 дня)
        pay_delay = random.randint(0, 1)
        pay_dt = created_at + timedelta(hours=random.randint(2, 6), days=pay_delay)
        # Не уходим в будущее
        if pay_dt.date() > date(2026, 3, 15):
            pay_dt = created_at + timedelta(hours=3)

        db.execute(text("""
            INSERT INTO payments (order_id, amount, payment_method, status, created_at)
            VALUES (:oid, :amt, :method, 'succeeded', :cat)
        """), {"oid": order_id, "amt": total, "method": method, "cat": pay_dt.isoformat()})
        paid_amount = total
        created_payments += 1

    # paid_amount в заказ
    db.execute(text("UPDATE orders SET paid_amount=:p WHERE id=:id"),
               {"p": paid_amount, "id": order_id})

    created_orders += 1

db.commit()
print(f"  Создано заказов: {created_orders}")
print(f"  Создано платежей: {created_payments}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Итог
# ─────────────────────────────────────────────────────────────────────────────
totals = {
    "employees": db.execute(text("SELECT COUNT(*) FROM employees WHERE position='mechanic'")).scalar(),
    "orders":    db.execute(text("SELECT COUNT(*) FROM orders")).scalar(),
    "payments":  db.execute(text("SELECT COUNT(*) FROM payments")).scalar(),
}

rev_jan = db.execute(text("""
    SELECT COALESCE(SUM(amount),0) FROM payments 
    WHERE status='succeeded' AND created_at >= '2026-01-01' AND created_at < '2026-02-01'
""")).scalar()
rev_feb = db.execute(text("""
    SELECT COALESCE(SUM(amount),0) FROM payments 
    WHERE status='succeeded' AND created_at >= '2026-02-01' AND created_at < '2026-03-01'
""")).scalar()
rev_mar = db.execute(text("""
    SELECT COALESCE(SUM(amount),0) FROM payments 
    WHERE status='succeeded' AND created_at >= '2026-03-01' AND created_at <= '2026-03-15'
""")).scalar()

print("\n" + "="*55)
print("  Данные успешно загружены!")
print("="*55)
for k, v in totals.items():
    print(f"  {k:<12}: {v}")
print(f"\n  Выручка январь: {int(rev_jan):,} ₽".replace(",", " "))
print(f"  Выручка февраль: {int(rev_feb):,} ₽".replace(",", " "))
print(f"  Выручка март 1-15: {int(rev_mar):,} ₽".replace(",", " "))
print("="*55)

db.close()
