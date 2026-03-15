"""
Скрипт загрузки заказ-нарядов:
  — Февраль 2026: по 2 заказа на каждого из 15 клиентов (30 шт, статус completed/paid)
  — Март 2026: 5 заказов для 5 клиентов с разными статусами (для теста дашборда)

Запуск: из директории backend/ → python scripts/seed_orders.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()

# Очистка существующих заказов (seed идемпотентен)
print("→ Очистка старых заказов...")
db.execute(text("DELETE FROM payments WHERE order_id IN (SELECT id FROM orders WHERE number LIKE 'ORD-202602%' OR number LIKE 'ORD-202603%')"))
db.execute(text("DELETE FROM order_works WHERE order_id IN (SELECT id FROM orders WHERE number LIKE 'ORD-202602%' OR number LIKE 'ORD-202603%')"))
db.execute(text("DELETE FROM order_parts WHERE order_id IN (SELECT id FROM orders WHERE number LIKE 'ORD-202602%' OR number LIKE 'ORD-202603%')"))
db.execute(text("DELETE FROM orders WHERE number LIKE 'ORD-202602%' OR number LIKE 'ORD-202603%'"))
db.commit()

EMPLOYEE_ID = 1   # Борисов — менеджер-приёмщик
MECHANIC_ID = 2   # Петров — механик

# ── Helpers ────────────────────────────────────────────────────────────────────
_order_counter = {}

def make_number(date_str: str) -> str:
    day = date_str[:10].replace("-", "")
    _order_counter.setdefault(day, 0)
    _order_counter[day] += 1
    return f"ORD-{day}-{_order_counter[day]:04d}"


def calc_total(rows: list) -> Decimal:
    total = Decimal(0)
    for price, qty, disc in rows:
        total += Decimal(str(price)) * qty * (1 - Decimal(str(disc)) / 100)
    return total.quantize(Decimal("0.01"))


def insert_order(
    *,
    date_str: str,
    vehicle_id: int,
    status: str,
    mechanic_id,
    works: list,      # [(work_id, qty, price, discount_pct)]
    parts: list,      # [(part_id, qty, price, discount_pct)]
    paid: bool = True,
    payment_method: str = "cash",
    payment_date: str = None,
    recommendations: str = None,
    comments: str = None,
    created_at: str = None,
    completed_at: str = None,
) -> int:
    number = make_number(date_str)
    ts_created = created_at or f"{date_str} 10:00:00"

    works_total = calc_total([(p, q, d) for _, q, p, d in works])
    parts_total = calc_total([(p, q, d) for _, q, p, d in parts])
    total_amount = works_total + parts_total
    paid_amount = total_amount if paid else Decimal(0)

    # --- order ---
    r = db.execute(text("""
        INSERT INTO orders
            (number, vehicle_id, employee_id, mechanic_id, status,
             total_amount, paid_amount, recommendations, comments,
             created_at, completed_at)
        VALUES
            (:num, :veh, :emp, :mech, :st,
             :total, :paid, :rec, :com,
             :created, :completed)
    """), {
        "num": number, "veh": vehicle_id, "emp": EMPLOYEE_ID,
        "mech": mechanic_id, "st": status,
        "total": float(total_amount), "paid": float(paid_amount),
        "rec": recommendations, "com": comments,
        "created": ts_created,
        "completed": completed_at or (f"{date_str} 17:30:00" if status == "completed" else None),
    })
    order_id = r.lastrowid

    # --- works ---
    for work_id, qty, price, disc in works:
        item_total = Decimal(str(price)) * qty * (1 - Decimal(str(disc)) / 100)
        db.execute(text("""
            INSERT INTO order_works (order_id, work_id, quantity, price, discount, total)
            VALUES (:oid, :wid, :qty, :price, :disc, :total)
        """), {"oid": order_id, "wid": work_id, "qty": qty,
               "price": price, "disc": disc, "total": float(item_total)})

    # --- parts ---
    for part_id, qty, price, disc in parts:
        item_total = Decimal(str(price)) * qty * (1 - Decimal(str(disc)) / 100)
        db.execute(text("""
            INSERT INTO order_parts (order_id, part_id, quantity, price, discount, total)
            VALUES (:oid, :pid, :qty, :price, :disc, :total)
        """), {"oid": order_id, "pid": part_id, "qty": qty,
               "price": price, "disc": disc, "total": float(item_total)})

    # --- payment ---
    if paid and total_amount > 0:
        pay_date = payment_date or f"{date_str} 17:45:00"
        db.execute(text("""
            INSERT INTO payments (order_id, amount, payment_method, status, created_at)
            VALUES (:oid, :amt, :method, 'succeeded', :ts)
        """), {"oid": order_id, "amt": float(total_amount),
               "method": payment_method, "ts": pay_date})

    return order_id


# ══════════════════════════════════════════════════════════════════════════════
# ФЕВРАЛЬ 2026 — 30 завершённых заказов (2 на клиента)
# vehicle_id 3–17 → customer_id 3–17
# ══════════════════════════════════════════════════════════════════════════════
print("→ Февраль: вставка 30 заказов...")

feb_orders = [

    # ── 1. МОРОЗОВ — Toyota Camry (vid=3) ─────────────────────────────────────
    dict(
        date_str="2026-02-03", vehicle_id=3, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),   # Замена масла и фильтра
            (2,  1,  400, 0),   # Замена воздушного фильтра
            (21, 1, 1200, 0),   # Замена свечей
        ],
        parts=[
            (6,  1,  490, 0),   # Фильтр масляный MANN
            (11, 4, 3200, 0),   # Масло Castrol 4L
            (8,  1,  720, 0),   # Фильтр воздушный MANN
            (26, 4,  420, 0),   # Свечи NGK (4 шт)
        ],
        payment_method="card",
        recommendations="Следующее ТО через 10 000 км или 12 месяцев",
    ),
    dict(
        date_str="2026-02-17", vehicle_id=3, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (26, 1, 2000, 0),   # Колодки передние
            (27, 1, 1800, 0),   # Колодки задние
            (6,  1,  850, 0),   # Тормозная жидкость
        ],
        parts=[
            (16, 1, 2400, 0),   # Колодки перед Brembo
            (17, 1, 2100, 0),   # Колодки зад Brembo
            (14, 1,  360, 0),   # Тормозная жидкость
        ],
        payment_method="cash",
        recommendations="Диски в норме, следующая замена колодок ~30 000 км",
    ),

    # ── 2. СОКОЛОВА — VW Polo (vid=4) ─────────────────────────────────────────
    dict(
        date_str="2026-02-05", vehicle_id=4, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (3,  1,  450, 0),   # Фильтр салона
            (13, 1, 1500, 0),   # Компьютерная диагностика
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
            (9,  1,  680, 0),   # Фильтр салонный
        ],
        payment_method="card",
    ),
    dict(
        date_str="2026-02-20", vehicle_id=4, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (18, 1, 6000, 0),   # Замена ремня ГРМ с роликами
        ],
        parts=[
            (21, 1, 1800, 0),   # Ремень ГРМ Gates
            (22, 1, 1400, 0),   # Ролик натяжной
            (23, 1, 1200, 0),   # Ролик обводной
        ],
        payment_method="cash",
        recommendations="Следующая замена ремня ГРМ через 60 000 км",
    ),

    # ── 3. НОВИКОВ — KIA Rio (vid=5) ──────────────────────────────────────────
    dict(
        date_str="2026-02-06", vehicle_id=5, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (34, 1, 1200, 0),   # Стойки стаба
            (33, 1, 2200, 0),   # Наконечники рулевых тяг
            (8,  1, 1800, 0),   # Развал-схождение
        ],
        parts=[
            (34, 2,  980, 0),   # Стойки стаба (2 шт)
            (33, 2, 1600, 0),   # Наконечники (2 шт)
        ],
        payment_method="card",
    ),
    dict(
        date_str="2026-02-18", vehicle_id=5, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (10, 1, 1600, 0),   # Шиномонтаж
            (9,  1,  800, 0),   # Балансировка
        ],
        parts=[],
        payment_method="cash",
    ),

    # ── 4. КОЗЛОВА — Hyundai Creta (vid=6) ────────────────────────────────────
    dict(
        date_str="2026-02-07", vehicle_id=6, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (3,  1,  450, 0),
            (5,  1,  800, 0),   # Антифриз
        ],
        parts=[
            (7,  1,  520, 0),   # Фильтр масляный Bosch
            (12, 4, 2900, 0),   # Масло Mobil
            (8,  1,  720, 0),
            (9,  1,  680, 0),
            (13, 1,  720, 0),   # Антифриз Sintec
        ],
        payment_method="card",
        recommendations="ТО пройдено, следующее через 15 000 км",
    ),
    dict(
        date_str="2026-02-19", vehicle_id=6, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (16, 1, 2000, 0),   # Диагностика электрики
            (37, 1, 2000, 0),   # Замена датчика ABS
        ],
        parts=[
            (38, 1, 2800, 0),   # Датчик ABS задний
        ],
        payment_method="cash",
        comments="Клиент сообщал о срабатывании ABS при торможении",
    ),

    # ── 5. ПЕТРОВ — BMW 3-series (vid=7) ──────────────────────────────────────
    dict(
        date_str="2026-02-08", vehicle_id=7, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 5),   # Замена масла (скидка 5% — VIP)
            (2,  1,  400, 5),
            (3,  1,  450, 5),
            (13, 1, 1500, 5),   # Диагностика
        ],
        parts=[
            (6,  1,  490, 5),
            (11, 5, 3200, 5),   # 5L масла для BMW
            (8,  1,  720, 5),
            (9,  1,  680, 5),
        ],
        payment_method="card",
        comments="VIP-клиент, скидка 5%",
    ),
    dict(
        date_str="2026-02-21", vehicle_id=7, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (30, 1, 4500, 5),   # Амортизаторы передние
            (8,  1, 1800, 5),   # Развал-схождение в подарок
        ],
        parts=[
            (29, 2, 5200, 5),   # Амортизаторы KYB (2 шт)
            (31, 2, 2000, 5),   # Опоры амортизаторов
        ],
        payment_method="card",
        recommendations="Задние амортизаторы в норме, контроль через 20 000 км",
    ),

    # ── 6. ЛЕБЕДЕВА — Toyota RAV4 (vid=8) ─────────────────────────────────────
    dict(
        date_str="2026-02-10", vehicle_id=8, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (3,  1,  450, 0),
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
            (8,  1,  720, 0),
            (9,  1,  680, 0),
        ],
        payment_method="cash",
    ),
    dict(
        date_str="2026-02-22", vehicle_id=8, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (28, 1, 2800, 0),   # Диски передние
            (26, 1, 2000, 0),   # Колодки передние
            (6,  1,  850, 0),   # Тормозная жидкость
        ],
        parts=[
            (18, 2, 4200, 0),   # Диски Brembo (2 шт)
            (16, 1, 2400, 0),   # Колодки Brembo
            (14, 1,  360, 0),
        ],
        payment_method="card",
        recommendations="Задние диски требуют замены при следующем ТО",
    ),

    # ── 7. ЗАХАРОВ — VW Tiguan (vid=9) ────────────────────────────────────────
    dict(
        date_str="2026-02-11", vehicle_id=9, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (13, 1, 1500, 0),   # Диагностика двигателя
            (24, 1, 1500, 0),   # Замена катушки зажигания
        ],
        parts=[
            (39, 1, 3200, 0),   # Катушка зажигания Bosch
        ],
        payment_method="cash",
        comments="Клиент жаловался на нестабильный холостой ход",
    ),
    dict(
        date_str="2026-02-23", vehicle_id=9, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (10, 1, 1600, 0),   # Шиномонтаж
            (9,  1,  800, 0),   # Балансировка
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
        ],
        payment_method="card",
    ),

    # ── 8. ПОПОВА — Audi A4 (vid=10) ──────────────────────────────────────────
    dict(
        date_str="2026-02-12", vehicle_id=10, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (20, 1, 4200, 0),   # Замена помпы
            (18, 1, 6000, 0),   # Ремень ГРМ заодно
        ],
        parts=[
            (24, 1, 3500, 0),   # Помпа водяная GMB
            (21, 1, 1800, 0),   # Ремень ГРМ
            (22, 1, 1400, 0),   # Ролик натяжной
            (23, 1, 1200, 0),   # Ролик обводной
        ],
        payment_method="card",
        recommendations="Следующая замена ремня ГРМ через 60 000 км",
    ),
    dict(
        date_str="2026-02-24", vehicle_id=10, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (16, 1, 2000, 0),   # Диагностика электрики
            (25, 1, 3000, 0),   # Замена лямбда-зонда
        ],
        parts=[
            (37, 1, 4800, 0),   # Лямбда-зонд Bosch
        ],
        payment_method="cash",
    ),

    # ── 9. СМИРНОВ — Mercedes C-class (vid=11) ────────────────────────────────
    dict(
        date_str="2026-02-13", vehicle_id=11, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (3,  1,  450, 0),
            (13, 1, 1500, 0),
        ],
        parts=[
            (7,  1,  520, 0),   # Bosch фильтр масла (для Mercedes)
            (11, 6, 3200, 0),   # Масло 6L (V6 двигатель)
            (8,  1,  720, 0),
            (9,  1,  680, 0),
        ],
        payment_method="card",
        comments="Зарегистрировано ТО в бортовом компьютере через диагностику",
    ),
    dict(
        date_str="2026-02-25", vehicle_id=11, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (34, 1, 1200, 0),   # Стойки стаба
            (8,  1, 1800, 0),   # Развал-схождение
        ],
        parts=[
            (34, 4,  980, 0),   # Стойки стаба (4 шт — перед и зад)
        ],
        payment_method="cash",
    ),

    # ── 10. КУЗНЕЦОВА — Honda CR-V (vid=12) ───────────────────────────────────
    dict(
        date_str="2026-02-14", vehicle_id=12, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (3,  1,  450, 0),
            (5,  1,  800, 0),
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
            (9,  1,  680, 0),
            (13, 1,  720, 0),
        ],
        payment_method="card",
    ),
    dict(
        date_str="2026-02-26", vehicle_id=12, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (14, 1, 1000, 0),   # Диагностика ходовой
            (32, 1, 3000, 0),   # Замена шаровых опор
            (8,  1, 1800, 0),   # Развал-схождение
        ],
        parts=[
            (32, 2, 2400, 0),   # Шаровые опоры Moog (2 шт)
        ],
        payment_method="cash",
    ),

    # ── 11. ВОЛКОВ — Skoda Octavia (vid=13) ───────────────────────────────────
    dict(
        date_str="2026-02-15", vehicle_id=13, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (4,  1,  900, 0),   # Топливный фильтр
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
            (8,  1,  720, 0),
            (10, 1,  980, 0),   # Топливный фильтр WIX
        ],
        payment_method="cash",
    ),
    dict(
        date_str="2026-02-27", vehicle_id=13, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (5,  1,  800, 0),   # Антифриз
            (7,  1,  700, 0),   # Жидкость ГУР
            (6,  1,  850, 0),   # Тормозная жидкость
        ],
        parts=[
            (13, 2,  720, 0),   # Антифриз (2 канистры)
            (15, 1,  490, 0),   # Жидкость ГУР
            (14, 1,  360, 0),
        ],
        payment_method="card",
        recommendations="Все технические жидкости заменены, состояние отличное",
    ),

    # ── 12. ОРЛОВА — Renault Logan (vid=14) ───────────────────────────────────
    dict(
        date_str="2026-02-16", vehicle_id=14, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (26, 1, 2000, 0),   # Колодки передние
            (27, 1, 1800, 0),   # Колодки задние
        ],
        parts=[
            (16, 1, 2400, 0),
            (17, 1, 2100, 0),
        ],
        payment_method="cash",
        comments="Клиент отметил скрип при торможении",
    ),
    dict(
        date_str="2026-02-28", vehicle_id=14, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (10, 1, 1600, 0),   # Шиномонтаж
            (9,  1,  800, 0),
        ],
        parts=[],
        payment_method="cash",
    ),

    # ── 13. СТЕПАНОВ — Lada Vesta (vid=15) ────────────────────────────────────
    dict(
        date_str="2026-02-03", vehicle_id=15, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (3,  1,  450, 0),
        ],
        parts=[
            (6,  1,  490, 0),
            (11, 4, 3200, 0),
            (8,  1,  720, 0),
            (9,  1,  680, 0),
        ],
        payment_method="cash",
    ),
    dict(
        date_str="2026-02-17", vehicle_id=15, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (13, 1, 1500, 0),   # Диагностика
            (21, 1, 1200, 0),   # Свечи
        ],
        parts=[
            (26, 4,  420, 0),   # Свечи NGK (4 шт)
        ],
        payment_method="card",
    ),

    # ── 14. БЕЛОВА — KIA Sportage (vid=16) ────────────────────────────────────
    dict(
        date_str="2026-02-04", vehicle_id=16, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (35, 1, 3800, 0),   # Замена ступичного подшипника
            (14, 1, 1000, 0),   # Диагностика ходовой
        ],
        parts=[
            (35, 1, 3600, 0),   # Ступичный подшипник FAG
        ],
        payment_method="cash",
        comments="Клиент жаловался на гул при движении",
    ),
    dict(
        date_str="2026-02-18", vehicle_id=16, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 0),
            (2,  1,  400, 0),
            (3,  1,  450, 0),
        ],
        parts=[
            (7,  1,  520, 0),
            (12, 4, 2900, 0),
            (8,  1,  720, 0),
            (9,  1,  680, 0),
        ],
        payment_method="card",
    ),

    # ── 15. НИКИТИН — BMW X5 (vid=17) ─────────────────────────────────────────
    dict(
        date_str="2026-02-05", vehicle_id=17, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (1,  1, 1200, 7),   # ТО BMW, скидка 7%
            (2,  1,  400, 7),
            (3,  1,  450, 7),
            (13, 1, 1500, 7),
        ],
        parts=[
            (7,  1,  520, 7),
            (11, 7, 3200, 7),   # 7L масла BMW X5 V8
            (8,  1,  720, 7),
            (9,  1,  680, 7),
        ],
        payment_method="card",
        comments="Флотский договор, скидка 7%, акт № Ф-2502",
    ),
    dict(
        date_str="2026-02-19", vehicle_id=17, mechanic_id=MECHANIC_ID,
        status="completed",
        works=[
            (31, 1, 3500, 7),   # Амортизаторы задние
        ],
        parts=[
            (30, 2, 4400, 7),   # Амортизаторы задние KYB (2 шт)
        ],
        payment_method="card",
        comments="Флотский договор, скидка 7%, акт № Ф-2503",
        recommendations="Передние амортизаторы допустимые, плановая замена через 15 000 км",
    ),
]

for o in feb_orders:
    insert_order(**o)

db.commit()
print(f"  Вставлено февральских заказов: {len(feb_orders)}")

# ══════════════════════════════════════════════════════════════════════════════
# МАРТ 2026 — 5 заказов с разными статусами (специально для теста дашборда)
# Сегодня: 08.03.2026
# ══════════════════════════════════════════════════════════════════════════════
print("\n→ Март: вставка 5 заказов для дашборда...")

# 1. МОРОЗОВ (vid=3) — in_progress с 03.03 → ЗАВИСШИЙ (5 дней!) ─────────────
# Замена ремня ГРМ, длинная работа, «застряла»
oid1 = insert_order(
    date_str="2026-03-03", vehicle_id=3, mechanic_id=MECHANIC_ID,
    status="in_progress",
    works=[(18, 1, 6000, 0)],   # Ремень ГРМ
    parts=[(21, 1, 1800, 0), (22, 1, 1400, 0), (23, 1, 1200, 0)],
    paid=False,
    created_at="2026-03-03 09:15:00",
    comments="Ждём запчасти от поставщика, помпа под вопросом",
)

# 2. ЗАХАРОВ (vid=9) — in_progress с 05.03 → ЗАВИСШИЙ (3 дня) ───────────────
# Замена амортизаторов, обнаружили доп. работы
oid2 = insert_order(
    date_str="2026-03-05", vehicle_id=9, mechanic_id=MECHANIC_ID,
    status="in_progress",
    works=[(30, 1, 4500, 0), (32, 1, 3000, 0)],   # Аморт. перед + шаровые
    parts=[(29, 2, 5200, 0), (32, 2, 2400, 0), (31, 2, 2000, 0)],
    paid=False,
    created_at="2026-03-05 10:30:00",
    comments="При разборке обнаружили износ шаровых, согласовали с клиентом",
)

# 3. ПЕТРОВ (vid=7, BMW 3) — ready_for_payment с 06.03 → НЕОПЛАЧЕННЫЙ ────────
# Диагностика + замена аккумулятора, давно ждёт оплату
oid3 = insert_order(
    date_str="2026-03-06", vehicle_id=7, mechanic_id=MECHANIC_ID,
    status="ready_for_payment",
    works=[(16, 1, 2000, 5), (36, 1, 600, 5)],   # Диагностика + аккумулятор
    parts=[(36, 1, 7500, 5)],                       # Аккумулятор Varta
    paid=False,
    created_at="2026-03-06 11:00:00",
    recommendations="Проверить зарядку через 1 месяц",
    comments="Клиент обещал оплатить завтра при получении авто",
)

# 4. СМИРНОВ (vid=11, Mercedes) — new, БЕЗ МЕХАНИКА → АЛЕРТ ─────────────────
# Только что создан, ещё не назначен
oid4 = insert_order(
    date_str="2026-03-08", vehicle_id=11, mechanic_id=None,   # ← без механика!
    status="new",
    works=[(13, 1, 1500, 0), (15, 1, 800, 0)],  # Диагностика двигателя + тормозов
    parts=[],
    paid=False,
    created_at="2026-03-08 08:45:00",
    comments="Клиент приехал без записи, жалуется на посторонний звук при торможении",
)

# 5. НИКИТИН (vid=17, BMW X5) — paid СЕГОДНЯ → ВЫРУЧКА В ДАШБОРДЕ ─────────────
# Замена лямбда-зонда, оплатил сегодня картой
oid5 = insert_order(
    date_str="2026-03-08", vehicle_id=17, mechanic_id=MECHANIC_ID,
    status="paid",
    works=[(25, 1, 3000, 7)],   # Замена лямбда-зонда, скидка 7%
    parts=[(37, 1, 4800, 7)],   # Лямбда-зонд Bosch
    paid=True,
    payment_method="card",
    payment_date="2026-03-08 14:20:00",
    created_at="2026-03-08 09:00:00",
    comments="Флотский договор, скидка 7%",
    recommendations="Проверить состав смеси через 1 000 км после адаптации",
)

db.commit()
print(f"  Вставлено мартовских заказов: 5")

# ══════════════════════════════════════════════════════════════════════════════
# ИТОГОВАЯ СТАТИСТИКА
# ══════════════════════════════════════════════════════════════════════════════
stats = {
    "orders (total)":              db.execute(text("SELECT COUNT(*) FROM orders")).scalar(),
    "orders (completed)":          db.execute(text("SELECT COUNT(*) FROM orders WHERE status='completed'")).scalar(),
    "orders (paid)":               db.execute(text("SELECT COUNT(*) FROM orders WHERE status='paid'")).scalar(),
    "orders (ready_for_payment)":  db.execute(text("SELECT COUNT(*) FROM orders WHERE status='ready_for_payment'")).scalar(),
    "orders (in_progress)":        db.execute(text("SELECT COUNT(*) FROM orders WHERE status='in_progress'")).scalar(),
    "orders (new)":                db.execute(text("SELECT COUNT(*) FROM orders WHERE status='new'")).scalar(),
    "order_works rows":            db.execute(text("SELECT COUNT(*) FROM order_works")).scalar(),
    "order_parts rows":            db.execute(text("SELECT COUNT(*) FROM order_parts")).scalar(),
    "payments":                    db.execute(text("SELECT COUNT(*) FROM payments")).scalar(),
}

rev_feb = db.execute(text("""
    SELECT COALESCE(SUM(p.amount),0) FROM payments p
    WHERE p.status='succeeded' AND strftime('%Y-%m', p.created_at)='2026-02'
""")).scalar()

rev_today = db.execute(text("""
    SELECT COALESCE(SUM(p.amount),0) FROM payments p
    WHERE p.status='succeeded' AND date(p.created_at)='2026-03-08'
""")).scalar()

print("\n" + "=" * 58)
print("  Заказ-наряды успешно загружены!")
print("=" * 58)
for k, v in stats.items():
    print(f"  {k:<30}: {v}")
print("-" * 58)
print(f"  Выручка февраль 2026       : {float(rev_feb):>12,.0f} ₽")
print(f"  Выручка сегодня (08.03)    : {float(rev_today):>12,.0f} ₽")
print("=" * 58)

print("\n  Дашборд-алерты которые увидите:")
print("  🔴 Зависшие в работе: заказы Морозова (5д) и Захарова (3д)")
print("  🔴 Неоплачено: заказ Петрова (BMW 3, 2+ дня)")
print("  🟡 Без механика: заказ Смирнова (Mercedes)")
print("  🟢 Выручка сегодня: оплата Никитина (BMW X5)")

db.close()
