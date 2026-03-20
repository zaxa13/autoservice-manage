"""
Seed orders from 14 to 20 March 2026.
Includes several orders with multiple mechanics per work line.
Run: python scripts/seed_orders_mar14_20.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from decimal import Decimal
from app.database import SessionLocal
from app.models.order import Order, OrderWork, OrderPart, OrderStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus

db = SessionLocal()

# ── helpers ───────────────────────────────────────────────────────────────────

MECHANIC_IDS = {
    "ivanov":  2,   # Иванов Сергей Петрович
    "klimov":  3,   # Климов Андрей Викторович
    "zaitsev": 4,   # Зайцев Николай Олегович
}
MANAGER_ID = 1  # Администратор

def dt(date_str: str, hour: int = 10, minute: int = 0) -> datetime:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.replace(hour=hour, minute=minute)

def make_order_number(db, date_str: str) -> str:
    tag = date_str.replace("-", "")
    existing = db.query(Order).filter(Order.number.like(f"ORD-{tag}-%")).all()
    return f"ORD-{tag}-{len(existing)+1:04d}"

def add_work(order_id, work_id, mechanic_id, qty=1, price=None, discount=0):
    from app.models.work import Work
    w = db.query(Work).filter(Work.id == work_id).first()
    p = Decimal(str(price)) if price is not None else w.price
    disc = Decimal(str(discount))
    total = p * qty * (1 - disc / 100)
    ow = OrderWork(
        order_id=order_id,
        work_id=work_id,
        work_name=w.name,
        mechanic_id=mechanic_id,
        quantity=qty,
        price=p,
        discount=disc,
        total=total,
    )
    db.add(ow)
    return total

def pay(order_id, amount, method=PaymentMethod.CASH, paid_at=None):
    p = Payment(
        order_id=order_id,
        amount=Decimal(str(amount)),
        payment_method=method,
        status=PaymentStatus.SUCCEEDED,
        created_at=paid_at or datetime.utcnow(),
    )
    db.add(p)
    return Decimal(str(amount))

# ── ORDER 1 ── 14 Mar ─────────────────────────────────────────────────────────
# BMW X5 (v15) — капремонт: Иванов делает двигатель, Климов — подвеску
o1 = Order(
    number=make_order_number(db, "2026-03-14"),
    vehicle_id=15,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-14", 9, 0),
    completed_at=dt("2026-03-14", 18, 0),
)
db.add(o1); db.flush()

t = Decimal(0)
t += add_work(o1.id, 13,  MECHANIC_IDS["ivanov"])   # Диагностика двигателя 1500
t += add_work(o1.id, 61,  MECHANIC_IDS["ivanov"])   # Замена ремня ГРМ 5000
t += add_work(o1.id, 64,  MECHANIC_IDS["ivanov"])   # Замена помпы при ГРМ 1500
t += add_work(o1.id, 58,  MECHANIC_IDS["ivanov"])   # Замена свечей (4 цил) 1200
t += add_work(o1.id, 101, MECHANIC_IDS["klimov"])   # Замена передних амортизаторов 4000
t += add_work(o1.id, 102, MECHANIC_IDS["klimov"])   # Замена задних амортизаторов 3000
t += add_work(o1.id, 108, MECHANIC_IDS["klimov"])   # Замена шаровой опоры 1500
t += add_work(o1.id, 119, MECHANIC_IDS["klimov"])   # Развал-схождение 2 оси 2500
o1.total_amount = t; o1.paid_amount = pay(o1.id, t, PaymentMethod.CARD, dt("2026-03-14", 18, 30))
db.flush()

# ── ORDER 2 ── 14 Mar ─────────────────────────────────────────────────────────
# Toyota Camry (v1) — ТО + электрика: Иванов ТО, Зайцев — электрика
o2 = Order(
    number=make_order_number(db, "2026-03-14"),
    vehicle_id=1,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["zaitsev"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-14", 11, 0),
    completed_at=dt("2026-03-14", 16, 0),
)
db.add(o2); db.flush()

t = Decimal(0)
t += add_work(o2.id, 1,   MECHANIC_IDS["ivanov"])   # Замена масла и фильтра 1200
t += add_work(o2.id, 2,   MECHANIC_IDS["ivanov"])   # Воздушный фильтр 400
t += add_work(o2.id, 3,   MECHANIC_IDS["ivanov"])   # Фильтр салона 450
t += add_work(o2.id, 16,  MECHANIC_IDS["zaitsev"])  # Диагностика электрики 2000
t += add_work(o2.id, 36,  MECHANIC_IDS["zaitsev"])  # Замена аккумулятора 600
t += add_work(o2.id, 8,   MECHANIC_IDS["zaitsev"])  # Развал-схождение 1800
o2.total_amount = t; o2.paid_amount = pay(o2.id, t, PaymentMethod.CASH, dt("2026-03-14", 16, 30))
db.flush()

# ── ORDER 3 ── 15 Mar ─────────────────────────────────────────────────────────
# Audi A4 (v8) — тормоза + кузов: Климов тормоза, Иванов кузов
o3 = Order(
    number=make_order_number(db, "2026-03-15"),
    vehicle_id=8,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["klimov"],
    status=OrderStatus.PAID,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-15", 10, 0),
    completed_at=dt("2026-03-15", 17, 0),
)
db.add(o3); db.flush()

t = Decimal(0)
t += add_work(o3.id, 122, MECHANIC_IDS["klimov"])   # Передние тормозные колодки 1500
t += add_work(o3.id, 123, MECHANIC_IDS["klimov"])   # Задние тормозные колодки 1500
t += add_work(o3.id, 124, MECHANIC_IDS["klimov"])   # Передние тормозные диски 2500
t += add_work(o3.id, 6,   MECHANIC_IDS["klimov"])   # Замена тормозной жидкости 850
t += add_work(o3.id, 224, MECHANIC_IDS["ivanov"])   # Удаление вмятин PDR 3000
t += add_work(o3.id, 237, MECHANIC_IDS["ivanov"])   # Ремонт скола стекла 1000
o3.total_amount = t; o3.paid_amount = pay(o3.id, t, PaymentMethod.CASH, dt("2026-03-15", 17, 30))
db.flush()

# ── ORDER 4 ── 15 Mar ─────────────────────────────────────────────────────────
# Volkswagen Polo (v2) — только шиномонтаж, Зайцев
o4 = Order(
    number=make_order_number(db, "2026-03-15"),
    vehicle_id=2,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["zaitsev"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-15", 12, 0),
    completed_at=dt("2026-03-15", 14, 0),
)
db.add(o4); db.flush()

t = Decimal(0)
t += add_work(o4.id, 254, MECHANIC_IDS["zaitsev"])  # Шиномонтаж R13-16 2000
t += add_work(o4.id, 9,   MECHANIC_IDS["zaitsev"])  # Балансировка 800
o4.total_amount = t; o4.paid_amount = pay(o4.id, t, PaymentMethod.CASH, dt("2026-03-15", 14, 15))
db.flush()

# ── ORDER 5 ── 16 Mar ─────────────────────────────────────────────────────────
# Mercedes C (v9) — комплексный: все три механика
o5 = Order(
    number=make_order_number(db, "2026-03-16"),
    vehicle_id=9,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-16", 9, 0),
    completed_at=dt("2026-03-17", 17, 0),
)
db.add(o5); db.flush()

t = Decimal(0)
# Иванов — двигатель и ТО
t += add_work(o5.id, 13,  MECHANIC_IDS["ivanov"])   # Диагностика двигателя 1500
t += add_work(o5.id, 56,  MECHANIC_IDS["ivanov"])   # Замена масла 800
t += add_work(o5.id, 57,  MECHANIC_IDS["ivanov"])   # Маслянный фильтр 200
t += add_work(o5.id, 72,  MECHANIC_IDS["ivanov"])   # Регулировка клапанов 3000
# Климов — подвеска
t += add_work(o5.id, 14,  MECHANIC_IDS["klimov"])   # Диагностика ходовой 1000
t += add_work(o5.id, 106, MECHANIC_IDS["klimov"])   # Сайлентблоки переднего рычага 3000
t += add_work(o5.id, 115, MECHANIC_IDS["klimov"])   # Рулевой наконечник 1000
t += add_work(o5.id, 109, MECHANIC_IDS["klimov"])   # Стойка стабилизатора 800
# Зайцев — электрика и климат
t += add_work(o5.id, 42,  MECHANIC_IDS["zaitsev"])  # Диагностика электросистем 2000
t += add_work(o5.id, 203, MECHANIC_IDS["zaitsev"])  # Заправка кондиционера 2500
t += add_work(o5.id, 207, MECHANIC_IDS["zaitsev"])  # Замена фильтра салона 500
o5.total_amount = t; o5.paid_amount = pay(o5.id, t, PaymentMethod.CARD, dt("2026-03-17", 17, 30))
db.flush()

# ── ORDER 6 ── 17 Mar ─────────────────────────────────────────────────────────
# Honda CR-V (v10) — ГРМ + охлаждение: Иванов двигатель, Климов охлаждение
o6 = Order(
    number=make_order_number(db, "2026-03-17"),
    vehicle_id=10,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.PAID,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-17", 10, 0),
    completed_at=dt("2026-03-17", 18, 0),
)
db.add(o6); db.flush()

t = Decimal(0)
t += add_work(o6.id, 62,  MECHANIC_IDS["ivanov"])   # Замена цепи ГРМ 12000
t += add_work(o6.id, 63,  MECHANIC_IDS["ivanov"])   # Натяжитель ГРМ 2000
t += add_work(o6.id, 169, MECHANIC_IDS["klimov"])   # Замена антифриза 1500
t += add_work(o6.id, 172, MECHANIC_IDS["klimov"])   # Замена термостата 2000
t += add_work(o6.id, 178, MECHANIC_IDS["klimov"])   # Промывка охлаждения 1500
o6.total_amount = t; o6.paid_amount = pay(o6.id, t, PaymentMethod.CASH, dt("2026-03-17", 18, 30))
db.flush()

# ── ORDER 7 ── 17 Mar ─────────────────────────────────────────────────────────
# Skoda Octavia (v11) — диагностика + шиномонтаж: Зайцев диагностика, Климов шины
o7 = Order(
    number=make_order_number(db, "2026-03-17"),
    vehicle_id=11,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["zaitsev"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-17", 11, 30),
    completed_at=dt("2026-03-17", 15, 0),
)
db.add(o7); db.flush()

t = Decimal(0)
t += add_work(o7.id, 13,  MECHANIC_IDS["zaitsev"])  # Диагностика двигателя 1500
t += add_work(o7.id, 40,  MECHANIC_IDS["zaitsev"])  # Диагностика ABS 1000
t += add_work(o7.id, 255, MECHANIC_IDS["klimov"])   # Шиномонтаж R17-R19 2800
t += add_work(o7.id, 9,   MECHANIC_IDS["klimov"])   # Балансировка 800
o7.total_amount = t; o7.paid_amount = pay(o7.id, t, PaymentMethod.CASH, dt("2026-03-17", 15, 30))
db.flush()

# ── ORDER 8 ── 18 Mar ─────────────────────────────────────────────────────────
# Renault Logan (v12) — ТО полное: Иванов (ТО), Зайцев (сезонная проверка)
o8 = Order(
    number=make_order_number(db, "2026-03-18"),
    vehicle_id=12,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-18", 9, 30),
    completed_at=dt("2026-03-18", 13, 0),
)
db.add(o8); db.flush()

t = Decimal(0)
t += add_work(o8.id, 1,   MECHANIC_IDS["ivanov"])   # Замена масла и фильтра 1200
t += add_work(o8.id, 2,   MECHANIC_IDS["ivanov"])   # Воздушный фильтр 400
t += add_work(o8.id, 3,   MECHANIC_IDS["ivanov"])   # Фильтр салона 450
t += add_work(o8.id, 4,   MECHANIC_IDS["ivanov"])   # Топливный фильтр 900
t += add_work(o8.id, 219, MECHANIC_IDS["zaitsev"])  # Сезонное обслуживание весна 2000
t += add_work(o8.id, 8,   MECHANIC_IDS["zaitsev"])  # Развал-схождение 1800
t += add_work(o8.id, 285, MECHANIC_IDS["zaitsev"])  # Сброс сервисного интервала 500
o8.total_amount = t; o8.paid_amount = pay(o8.id, t, PaymentMethod.CASH, dt("2026-03-18", 13, 30))
db.flush()

# ── ORDER 9 ── 18 Mar ─────────────────────────────────────────────────────────
# Toyota RAV4 (v6) — АКПП + ходовая: Иванов АКПП, Климов ходовая
o9 = Order(
    number=make_order_number(db, "2026-03-18"),
    vehicle_id=6,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.READY_FOR_PAYMENT,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-18", 14, 0),
    completed_at=dt("2026-03-18", 18, 0),
)
db.add(o9); db.flush()

t = Decimal(0)
t += add_work(o9.id, 39,  MECHANIC_IDS["zaitsev"])  # Диагностика АКПП 1500
t += add_work(o9.id, 82,  MECHANIC_IDS["ivanov"])   # Замена масла АКПП аппаратная 4000
t += add_work(o9.id, 100, MECHANIC_IDS["ivanov"])   # Адаптация АКПП 2000
t += add_work(o9.id, 103, MECHANIC_IDS["klimov"])   # Замена опорного подшипника 1500
t += add_work(o9.id, 110, MECHANIC_IDS["klimov"])   # Замена втулок стабилизатора 600
o9.total_amount = t; db.flush()

# ── ORDER 10 ── 19 Mar ────────────────────────────────────────────────────────
# BMW 3 (v5) — кузовной ремонт: Иванов рихтовка, Климов покраска
o10 = Order(
    number=make_order_number(db, "2026-03-19"),
    vehicle_id=5,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["klimov"],
    status=OrderStatus.IN_PROGRESS,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-19", 9, 0),
)
db.add(o10); db.flush()

t = Decimal(0)
t += add_work(o10.id, 223, MECHANIC_IDS["ivanov"])  # Рихтовка кузовного элемента 5000
t += add_work(o10.id, 224, MECHANIC_IDS["ivanov"])  # Удаление вмятин PDR 3000
t += add_work(o10.id, 247, MECHANIC_IDS["klimov"])  # Грунтовка элемента 2000
t += add_work(o10.id, 248, MECHANIC_IDS["klimov"])  # Шпатлёвка элемента 2000
t += add_work(o10.id, 242, MECHANIC_IDS["klimov"])  # Покраска элемента 8000
t += add_work(o10.id, 249, MECHANIC_IDS["klimov"])  # Полировка кузова 8000
o10.total_amount = t; db.flush()

# ── ORDER 11 ── 19 Mar ────────────────────────────────────────────────────────
# Hyundai Creta (v4) — простое ТО, один механик
o11 = Order(
    number=make_order_number(db, "2026-03-19"),
    vehicle_id=4,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["zaitsev"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-19", 11, 0),
    completed_at=dt("2026-03-19", 14, 0),
)
db.add(o11); db.flush()

t = Decimal(0)
t += add_work(o11.id, 215, MECHANIC_IDS["zaitsev"])  # ТО-2 5000
t += add_work(o11.id, 8,   MECHANIC_IDS["zaitsev"])  # Развал-схождение 1800
o11.total_amount = t; o11.paid_amount = pay(o11.id, t, PaymentMethod.CASH, dt("2026-03-19", 14, 30))
db.flush()

# ── ORDER 12 ── 20 Mar ────────────────────────────────────────────────────────
# Volkswagen Tiguan (v7) — трансмиссия + электрика: Иванов КПП, Зайцев электрика
o12 = Order(
    number=make_order_number(db, "2026-03-20"),
    vehicle_id=7,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["ivanov"],
    status=OrderStatus.IN_PROGRESS,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-20", 9, 0),
)
db.add(o12); db.flush()

t = Decimal(0)
t += add_work(o12.id, 39,  MECHANIC_IDS["zaitsev"])  # Диагностика АКПП 1500
t += add_work(o12.id, 93,  MECHANIC_IDS["ivanov"])   # Замена ШРУСа наружного 3000
t += add_work(o12.id, 95,  MECHANIC_IDS["ivanov"])   # Замена пыльника ШРУСа 2000
t += add_work(o12.id, 148, MECHANIC_IDS["zaitsev"])  # Замена генератора 3000
t += add_work(o12.id, 16,  MECHANIC_IDS["zaitsev"])  # Диагностика электрики 2000
o12.total_amount = t; db.flush()

# ── ORDER 13 ── 20 Mar ────────────────────────────────────────────────────────
# Toyota Camry (v1) — ещё раз, быстрая замена масла + шины: разные механики
o13 = Order(
    number=make_order_number(db, "2026-03-20"),
    vehicle_id=1,
    employee_id=MANAGER_ID,
    mechanic_id=MECHANIC_IDS["klimov"],
    status=OrderStatus.COMPLETED,
    total_amount=0, paid_amount=0,
    created_at=dt("2026-03-20", 10, 30),
    completed_at=dt("2026-03-20", 13, 0),
)
db.add(o13); db.flush()

t = Decimal(0)
t += add_work(o13.id, 1,   MECHANIC_IDS["ivanov"])   # Замена масла и фильтра 1200
t += add_work(o13.id, 254, MECHANIC_IDS["klimov"])   # Шиномонтаж R13-16 2000
t += add_work(o13.id, 9,   MECHANIC_IDS["klimov"])   # Балансировка 800
o13.total_amount = t; o13.paid_amount = pay(o13.id, t, PaymentMethod.CARD, dt("2026-03-20", 13, 15))
db.flush()

db.commit()
print(f"✓ Создано 13 заказов с 14 по 20 марта 2026")
print(f"  Заказы с несколькими механиками: #1, #2, #3, #5, #6, #7, #8, #9, #10, #12, #13")
print(f"  Статусы: completed/paid/ready_for_payment/in_progress")
db.close()
