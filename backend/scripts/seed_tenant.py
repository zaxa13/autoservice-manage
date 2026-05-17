"""Наполнение тенанта тестовыми данными: клиенты, машины, заказ-наряды.

Использование:
    python scripts/seed_tenant.py <tenant_id> [a|b]

Что создаёт:
    — 1 менеджер-приёмщик + 2 механика (если их ещё нет в тенанте);
    — 30 клиентов (3 из них — "shared" с фиксированными phone/email,
      одинаковыми между variant=a и variant=b → для проверки RLS-изоляции);
    — 30 автомобилей, по одному на клиента (3 "shared" с фиксированными
      VIN/license_plate);
    — ~140 заказ-нарядов за январь–май 2026 (30/30/30/30/20), статусы и
      платежи распределены реалистично; каждый "shared" автомобиль гарантированно
      получает минимум 2 наряда.

Работы и запчасти кладутся в заказ инлайн (через work_name/part_name) —
зависимости от каталогов `works`/`parts` нет.

Идемпотентность: повторный запуск удалит ранее созданные скриптом данные
(по marker-комментарию в `customers.notes`) и нальёт заново.
"""
import argparse
import asyncio
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import tenant_session

SEED_MARKER = "[seed_tenant.py]"


# ─────────────────────────────────────────────────────────────────────────────
# Справочные данные
# ─────────────────────────────────────────────────────────────────────────────

# Бренды/модели по name (id берём из vehicle_brands/vehicle_models).
BRAND_MODELS = [
    ("Toyota",   "Camry"),
    ("Toyota",   "Corolla"),
    ("Toyota",   "RAV4"),
    ("Volkswagen", "Polo"),
    ("Volkswagen", "Tiguan"),
    ("Volkswagen", "Passat"),
    ("KIA",      "Rio"),
    ("KIA",      "Sportage"),
    ("Hyundai",  "Creta"),
    ("Hyundai",  "Solaris"),
    ("Hyundai",  "Tucson"),
    ("BMW",      "3 серия"),
    ("BMW",      "5 серия"),
    ("BMW",      "X5"),
    ("Audi",     "A4"),
    ("Audi",     "Q5"),
    ("Mercedes-Benz", "C-класс"),
    ("Mercedes-Benz", "E-класс"),
    ("Honda",    "Civic"),
    ("Honda",    "CR-V"),
    ("Skoda",    "Octavia"),
    ("Skoda",    "Kodiaq"),
    ("Renault",  "Logan"),
    ("Renault",  "Duster"),
    ("LADA (ВАЗ)", "Vesta"),
    ("LADA (ВАЗ)", "Granta"),
    ("Mazda",    "CX-5"),
    ("Mazda",    "6"),
    ("Nissan",   "Qashqai"),
    ("Nissan",   "X-Trail"),
]

# 3 "shared" клиента: фиксированные phone/email — одинаковые для variant=a и b.
# Используются для проверки RLS-изоляции.
SHARED_CUSTOMERS = [
    ("Иванов Иван Иванович",     "+79990000001", "ivanov.shared@example.com",   "г. Москва, ул. Общая, 1"),
    ("Петрова Анна Сергеевна",   "+79990000002", "petrova.shared@example.com",  "г. Москва, ул. Общая, 2"),
    ("Сидоров Олег Викторович",  "+79990000003", "sidorov.shared@example.com", "г. Москва, ул. Общая, 3"),
]

# 3 "shared" авто: те же VIN/plate в обоих тенантах.
SHARED_VEHICLES = [
    # (vin, plate, brand_name, model_name, year)
    ("XW8ZZZ61ZGG000001", "О001АА777", "Toyota",     "Camry", 2021),
    ("VF1HJK20567890002", "О002АА777", "Volkswagen", "Polo",  2020),
    ("WDD2050463R000003", "О003АА777", "BMW",        "X5",    2022),
]

# Уникальные клиенты variant=a (27 шт.)
UNIQUE_CUSTOMERS_A = [
    ("Морозов Сергей Анатольевич",    "+79161234501", "morozov.sa@mail.ru",      "г. Москва, ул. Ленина, 12"),
    ("Соколова Татьяна Игоревна",     "+79261234502", "sokolova.ti@yandex.ru",   "г. Москва, ул. Садовая, 8"),
    ("Новиков Дмитрий Владимирович",  "+79031234503", "novikov.dv@gmail.com",    "г. Москва, пр-т Мира, 34"),
    ("Козлова Елена Павловна",        "+79671234504", "kozlova.ep@mail.ru",      "г. Люберцы, ул. Кирова, 5"),
    ("Петров Алексей Сергеевич",      "+79851234505", "petrov.as@yandex.ru",     "г. Москва, ул. Тверская, 22"),
    ("Лебедева Ирина Николаевна",     "+79151234506", None,                       "г. Красногорск, ул. Парковая, 7"),
    ("Захаров Виктор Михайлович",     "+79261234507", "zaharov.vm@mail.ru",      "г. Балашиха, ул. Советская, 18"),
    ("Попова Наталья Юрьевна",        "+79651234508", "popova.ny@gmail.com",     "г. Москва, ул. Профсоюзная, 44"),
    ("Смирнов Андрей Олегович",       "+79991234509", "smirnov.ao@yandex.ru",    "г. Мытищи, ул. Летная, 2"),
    ("Кузнецова Мария Александровна", "+79171234510", "kuznetsova.ma@mail.ru",   "г. Москва, ул. Арбат, 16"),
    ("Волков Константин Дмитриевич",  "+79381234511", None,                       "г. Химки, ул. Лавочкина, 10"),
    ("Орлова Людмила Васильевна",     "+79491234512", "orlova.lv@yandex.ru",     "г. Подольск, ул. Ленина, 33"),
    ("Степанов Роман Евгеньевич",     "+79771234513", "stepanov.re@gmail.com",   "г. Москва, Варшавское ш., 67"),
    ("Белова Ольга Анатольевна",      "+79561234514", "belova.oa@mail.ru",       "г. Долгопрудный, ул. Молодёжная, 4"),
    ("Никитин Игорь Петрович",        "+79091234515", "nikitin.ip@yandex.ru",    "г. Москва, ул. Нагатинская, 25"),
    ("Соловьёв Михаил Романович",     "+79161234516", "soloviev.mr@mail.ru",     "г. Реутов, ул. Победы, 9"),
    ("Гусева Анна Викторовна",        "+79261234517", "guseva.av@yandex.ru",     "г. Москва, ул. Дмитровская, 30"),
    ("Алексеев Павел Сергеевич",      "+79031234518", "alekseev.ps@gmail.com",   "г. Одинцово, ул. Молодёжная, 1"),
    ("Никифорова Ольга Юрьевна",      "+79671234519", "nikiforova.oy@mail.ru",   "г. Москва, ул. Зорге, 14"),
    ("Афанасьев Григорий Львович",    "+79851234520", "afanasiev.gl@yandex.ru",  "г. Видное, Жуковский пр., 6"),
    ("Тарасова Юлия Викторовна",      "+79151234521", "tarasova.yv@gmail.com",   "г. Москва, ул. Беговая, 11"),
    ("Васильев Денис Александрович",  "+79261234522", "vasiliev.da@mail.ru",     "г. Королёв, Циолковского, 22"),
    ("Романова Елизавета Юрьевна",    "+79651234523", "romanova.ey@yandex.ru",   "г. Москва, ул. Профсоюзная, 12"),
    ("Беляев Артём Геннадьевич",      "+79991234524", "belyaev.ag@gmail.com",    "г. Жуковский, ул. Гагарина, 4"),
    ("Сорокина Светлана Игоревна",    "+79171234525", "sorokina.si@mail.ru",     "г. Москва, ул. Перовская, 19"),
    ("Цветков Иван Андреевич",        "+79381234526", "tsvetkov.ia@yandex.ru",   "г. Котельники, ул. Кузьминская, 3"),
    ("Маркова Анастасия Сергеевна",   "+79491234527", "markova.as@gmail.com",    "г. Москва, ул. Кулакова, 7"),
]

UNIQUE_CUSTOMERS_B = [
    ("Кравцов Юрий Михайлович",       "+79991110001", "kravtsov.ym@mail.ru",     "г. Санкт-Петербург, Невский, 1"),
    ("Демидова Анастасия Сергеевна",  "+79991110002", "demidova.as@yandex.ru",   "г. Санкт-Петербург, Лиговский, 12"),
    ("Артемьев Олег Андреевич",       "+79991110003", "artemiev.oa@gmail.com",   "г. Санкт-Петербург, Лесной, 4"),
    ("Семёнова Елена Викторовна",     "+79991110004", "semenova.ev@mail.ru",     "г. Санкт-Петербург, Бассейная, 18"),
    ("Поляков Денис Алексеевич",      "+79991110005", "polyakov.da@yandex.ru",   "г. Санкт-Петербург, Гражданский, 55"),
    ("Куликова Светлана Юрьевна",     "+79991110006", None,                       "г. Санкт-Петербург, Просвещения, 87"),
    ("Большаков Игорь Сергеевич",     "+79991110007", "bolshakov.is@mail.ru",    "г. Санкт-Петербург, Маршала Захарова, 9"),
    ("Прохорова Ирина Алексеевна",    "+79991110008", "prokhorova.ia@gmail.com", "г. Санкт-Петербург, Кораблестроителей, 22"),
    ("Носов Александр Васильевич",    "+79991110009", "nosov.av@yandex.ru",      "г. Колпино, ул. Заводская, 11"),
    ("Гончарова Полина Романовна",    "+79991110010", "goncharova.pr@mail.ru",   "г. Санкт-Петербург, Шкиперский, 14"),
    ("Дроздов Кирилл Максимович",     "+79991110011", None,                       "г. Пушкин, Софийский б-р, 5"),
    ("Шестакова Татьяна Олеговна",    "+79991110012", "shestakova.to@yandex.ru", "г. Санкт-Петербург, Ветеранов, 102"),
    ("Зайцев Антон Михайлович",       "+79991110013", "zaitsev.am@gmail.com",    "г. Санкт-Петербург, Энгельса, 132"),
    ("Кириллова Ольга Сергеевна",     "+79991110014", "kirillova.os@mail.ru",    "г. Гатчина, ул. Чкалова, 7"),
    ("Леонов Сергей Викторович",      "+79991110015", "leonov.sv@yandex.ru",     "г. Санкт-Петербург, Просвещения, 33"),
    ("Васнецов Дмитрий Леонидович",   "+79991110016", "vasnetsov.dl@mail.ru",    "г. Санкт-Петербург, Кораблестроителей, 8"),
    ("Богданова Виктория Андреевна",  "+79991110017", "bogdanova.va@yandex.ru",  "г. Санкт-Петербург, Парашютная, 12"),
    ("Ефимов Артур Витальевич",       "+79991110018", "efimov.av@gmail.com",     "г. Кронштадт, ул. Восстания, 4"),
    ("Котова Маргарита Олеговна",     "+79991110019", "kotova.mo@mail.ru",       "г. Санкт-Петербург, Малая Морская, 9"),
    ("Лазарев Никита Алексеевич",     "+79991110020", "lazarev.na@yandex.ru",    "г. Санкт-Петербург, Большой пр., 67"),
    ("Гордеева Юлия Дмитриевна",      "+79991110021", "gordeeva.yd@gmail.com",   "г. Санкт-Петербург, Седова, 21"),
    ("Терентьев Виталий Игоревич",    "+79991110022", "terentiev.vi@mail.ru",    "г. Санкт-Петербург, Дыбенко, 39"),
    ("Ушакова Наталья Анатольевна",   "+79991110023", "ushakova.na@yandex.ru",   "г. Санкт-Петербург, Гражданский, 76"),
    ("Фёдоров Денис Григорьевич",     "+79991110024", "fedorov.dg@gmail.com",    "г. Сертолово, Восточно-Выборгское, 6"),
    ("Харитонова Анна Кирилловна",    "+79991110025", "kharitonova.ak@mail.ru",  "г. Санкт-Петербург, Каменноостровский, 38"),
    ("Чернов Олег Викторович",        "+79991110026", "chernov.ov@yandex.ru",    "г. Санкт-Петербург, Софийская, 12"),
    ("Щербакова Юлия Эдуардовна",     "+79991110027", "shcherbakova.ye@gmail.com","г. Санкт-Петербург, Авиаконструкторов, 5"),
]


def unique_vehicles(variant: str) -> list[tuple]:
    """27 авто, VIN/plate уникальны в пределах варианта (A или B)."""
    # Префиксы для разнесения VIN/plate между вариантами.
    vin_pref, plate_letter, plate_region = (
        ("1A", "М", "77") if variant == "a" else ("1B", "Т", "78")
    )
    out = []
    for i in range(27):
        idx = i + 1
        bm = BRAND_MODELS[(i + 3) % len(BRAND_MODELS)]  # без первых 3 (shared)
        vin = f"{vin_pref}{idx:015d}"                    # 17 символов
        plate = f"{plate_letter}{idx:03d}АВ{plate_region}"
        year = 2018 + (i % 7)
        out.append((vin, plate, bm[0], bm[1], year))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Сценарии работ/запчастей (инлайн, без FK)
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "comment": "Плановое ТО: масло + фильтры",
        "works": [("Замена моторного масла и фильтра", 1200), ("Замена воздушного фильтра", 400),
                  ("Замена фильтра салона", 450)],
        "parts": [("Масло Castrol Magnatec 5W-40 4L", "156EDD", 3200, 4),
                  ("Фильтр масляный MANN W712/94", "W712/94", 490, 1),
                  ("Фильтр воздушный MANN C27006", "C27006", 720, 1),
                  ("Фильтр салонный MANN CUK29005", "CUK29005", 680, 1)],
    },
    {
        "comment": "Замена тормозных колодок передних",
        "works": [("Замена тормозных колодок передних", 2000),
                  ("Замена тормозной жидкости", 850)],
        "parts": [("Колодки тормозные передние Brembo P85020", "P85020", 2400, 1),
                  ("Тормозная жидкость Sintec DOT4", "800553", 360, 1)],
    },
    {
        "comment": "Замена ремня ГРМ с роликами и помпой",
        "works": [("Замена ремня ГРМ с роликами", 6000),
                  ("Замена помпы (водяного насоса)", 4200)],
        "parts": [("Ремень ГРМ Gates T43053", "T43053", 1800, 1),
                  ("Ролик натяжной Gates T43127", "T43127", 1400, 1),
                  ("Ролик обводной Gates T36328", "T36328", 1200, 1),
                  ("Помпа водяная GMB GWKIA50A", "GWKIA50A", 3500, 1)],
    },
    {
        "comment": "Замена амортизаторов передних + развал-схождение",
        "works": [("Замена амортизаторов передних (2 шт.)", 4500),
                  ("Развал-схождение 3D", 1800)],
        "parts": [("Амортизатор передний KYB", "KYB334461", 5200, 2),
                  ("Опора амортизатора KYB", "SM5714", 2000, 2)],
    },
    {
        "comment": "Компьютерная диагностика двигателя",
        "works": [("Компьютерная диагностика двигателя", 1500)],
        "parts": [],
    },
    {
        "comment": "Замена аккумулятора + диагностика электрики",
        "works": [("Диагностика системы электрики", 2000),
                  ("Замена аккумулятора", 600)],
        "parts": [("Аккумулятор Varta Blue 60Ah", "560408054", 7500, 1)],
    },
    {
        "comment": "Шиномонтаж + балансировка",
        "works": [("Шиномонтаж комплект 4 колеса", 1600),
                  ("Балансировка колёс (4 шт.)", 800)],
        "parts": [],
    },
    {
        "comment": "Замена свечей зажигания",
        "works": [("Замена свечей зажигания", 1200)],
        "parts": [("Свечи зажигания NGK BKR6EGP", "BKR6EGP", 420, 4)],
    },
    {
        "comment": "Замена шаровых опор",
        "works": [("Замена шаровых опор передних", 3000),
                  ("Развал-схождение 3D", 1800)],
        "parts": [("Шаровая опора Moog", "MOSK8895", 2400, 2)],
    },
    {
        "comment": "Замена лямбда-зонда",
        "works": [("Диагностика системы электрики", 2000),
                  ("Замена лямбда-зонда", 3000)],
        "parts": [("Лямбда-зонд Bosch", "0258006537", 4800, 1)],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _next_order_number(db) -> str:
    await db.execute(text(
        "INSERT INTO app.tenant_counters (tenant_id, counter_name, value) "
        "VALUES (app.current_tenant(), 'orders', 0) "
        "ON CONFLICT (tenant_id, counter_name) DO NOTHING"
    ))
    r = await db.execute(text(
        "UPDATE app.tenant_counters SET value = value + 1 "
        "WHERE tenant_id = app.current_tenant() AND counter_name = 'orders' "
        "RETURNING value"
    ))
    return f"ЗН-{r.scalar_one():03d}"


async def _resolve_brand_model(db, brand_name: str, model_name: str) -> tuple[int, int]:
    """Найти brand_id/model_id по именам (vehicle_brands/vehicle_models — глобальные)."""
    r = await db.execute(text(
        "SELECT b.id AS brand_id, m.id AS model_id "
        "FROM app.vehicle_brands b "
        "JOIN app.vehicle_models m ON m.brand_id = b.id "
        "WHERE b.name = :bn AND m.name = :mn LIMIT 1"
    ), {"bn": brand_name, "mn": model_name})
    row = r.first()
    if not row:
        raise RuntimeError(f"vehicle_brands/models нет: {brand_name} / {model_name}")
    return row.brand_id, row.model_id


async def _wipe_previous_seed(db) -> None:
    """Удалить ранее созданные скриптом данные (по marker в customers.notes)."""
    marker_param = {"marker": f"%{SEED_MARKER}%"}

    # Сколько было — для лога
    r = await db.execute(text(
        "SELECT COUNT(*) FROM app.customers WHERE notes LIKE :marker"
    ), marker_param)
    n_prev = r.scalar_one()
    if not n_prev:
        return

    # Цепочка зависимостей: payments → order_works/parts → orders → vehicles → customers
    customer_filter = (
        "SELECT id FROM app.customers WHERE notes LIKE :marker"
    )
    vehicle_filter = (
        f"SELECT id FROM app.vehicles WHERE customer_id IN ({customer_filter})"
    )
    order_filter = (
        f"SELECT id FROM app.orders WHERE vehicle_id IN ({vehicle_filter})"
    )

    for sql in (
        f"DELETE FROM app.payments     WHERE order_id IN ({order_filter})",
        f"DELETE FROM app.order_works  WHERE order_id IN ({order_filter})",
        f"DELETE FROM app.order_parts  WHERE order_id IN ({order_filter})",
        f"DELETE FROM app.orders       WHERE vehicle_id IN ({vehicle_filter})",
        f"DELETE FROM app.vehicles     WHERE customer_id IN ({customer_filter})",
         "DELETE FROM app.customers    WHERE notes LIKE :marker",
    ):
        await db.execute(text(sql), marker_param)

    print(f"  Удалено клиентов предыдущего сида: {n_prev}")


async def _ensure_employees(db) -> tuple[int, list[int]]:
    """Вернуть (manager_id, [mechanic_ids]). Создать, если их нет."""
    r = await db.execute(text(
        "SELECT id FROM app.employees WHERE position IN ('admin','manager') "
        "AND is_active = true ORDER BY id LIMIT 1"
    ))
    row = r.first()
    if row:
        manager_id = row[0]
    else:
        r = await db.execute(text(
            "INSERT INTO app.employees "
            "(tenant_id, full_name, position, phone, hire_date, salary_base, is_active) "
            "VALUES (app.current_tenant(), :n, 'manager', :p, '2024-01-15', 80000, true) "
            "RETURNING id"
        ), {"n": "Борисов Антон Сергеевич (приёмщик)", "p": "+79261110000"})
        manager_id = r.scalar_one()
        print(f"  + создан менеджер id={manager_id}")

    r = await db.execute(text(
        "SELECT id FROM app.employees WHERE position = 'mechanic' "
        "AND is_active = true ORDER BY id"
    ))
    mech_ids = [row[0] for row in r.all()]
    if len(mech_ids) < 2:
        defaults = [
            ("Петров Иван Сергеевич",   "+79261110001", "2023-05-10", 65000),
            ("Климов Андрей Викторович","+79261110002", "2023-09-20", 60000),
        ]
        for full_name, phone, hire, sal in defaults[len(mech_ids):]:
            r = await db.execute(text(
                "INSERT INTO app.employees "
                "(tenant_id, full_name, position, phone, hire_date, salary_base, is_active) "
                "VALUES (app.current_tenant(), :n, 'mechanic', :p, :h, :s, true) "
                "RETURNING id"
            ), {"n": full_name, "p": phone, "h": hire, "s": sal})
            mech_ids.append(r.scalar_one())
            print(f"  + создан механик id={mech_ids[-1]} ({full_name})")
    return manager_id, mech_ids


# ─────────────────────────────────────────────────────────────────────────────
# Main seed
# ─────────────────────────────────────────────────────────────────────────────

async def seed(tenant_id: UUID, variant: str) -> None:
    print(f"\n=== Сид тенанта {tenant_id} (вариант '{variant}') ===")
    rng = random.Random(f"{tenant_id}-{variant}")

    customers_unique = UNIQUE_CUSTOMERS_A if variant == "a" else UNIQUE_CUSTOMERS_B
    vehicles_unique = unique_vehicles("A" if variant == "a" else "B")

    customers_all = SHARED_CUSTOMERS + customers_unique           # 30
    vehicles_all = SHARED_VEHICLES + vehicles_unique              # 30
    assert len(customers_all) == 30 and len(vehicles_all) == 30

    async with tenant_session(tenant_id) as db:
        # 0. Очистка предыдущего сида
        print("→ Очистка предыдущего сида...")
        await _wipe_previous_seed(db)

        # 1. Сотрудники
        print("→ Сотрудники...")
        manager_id, mech_ids = await _ensure_employees(db)
        print(f"  manager={manager_id}, mechanics={mech_ids}")

        # 2. Клиенты (30 шт.)
        print("→ Клиенты (30)...")
        customer_ids = []
        for i, (full_name, phone, email, address) in enumerate(customers_all):
            tag = "shared" if i < len(SHARED_CUSTOMERS) else f"unique-{variant}"
            r = await db.execute(text(
                "INSERT INTO app.customers "
                "(tenant_id, full_name, phone, email, address, notes) "
                "VALUES (app.current_tenant(), :n, :p, :e, :a, :notes) "
                "RETURNING id"
            ), {"n": full_name, "p": phone, "e": email, "a": address,
                "notes": f"{SEED_MARKER} {tag}"})
            customer_ids.append(r.scalar_one())

        # 3. Авто (30 шт.)
        print("→ Авто (30)...")
        vehicle_ids = []
        for i, (vin, plate, brand_name, model_name, year) in enumerate(vehicles_all):
            brand_id, model_id = await _resolve_brand_model(db, brand_name, model_name)
            mileage = rng.randint(15000, 180000)
            r = await db.execute(text(
                "INSERT INTO app.vehicles "
                "(tenant_id, vin, license_plate, brand_id, model_id, year, mileage, customer_id) "
                "VALUES (app.current_tenant(), :vin, :plate, :bid, :mid, :y, :km, :cid) "
                "RETURNING id"
            ), {"vin": vin, "plate": plate, "bid": brand_id, "mid": model_id,
                "y": year, "km": mileage, "cid": customer_ids[i]})
            vehicle_ids.append(r.scalar_one())

        # 4. Заказ-наряды Jan–May 2026
        print("→ Заказ-наряды (январь–май 2026)...")
        monthly_counts = {1: 30, 2: 30, 3: 30, 4: 30, 5: 20}     # = 140
        all_dates: list[date] = []
        for month, count in monthly_counts.items():
            for _ in range(count):
                day = rng.randint(1, 28)
                all_dates.append(date(2026, month, day))
        all_dates.sort()

        # Random vehicles, но гарантируем минимум 2 наряда на каждый shared (idx 0..2)
        shared_vid = vehicle_ids[:len(SHARED_VEHICLES)]
        vehicle_per_order = [rng.choice(vehicle_ids) for _ in all_dates]
        # Гарантия: для каждого shared — минимум 2 наряда в этом периоде
        for vid in shared_vid:
            existing = sum(1 for v in vehicle_per_order if v == vid)
            if existing < 2:
                # Подменяем случайные не-shared слоты
                need = 2 - existing
                non_shared_idxs = [i for i, v in enumerate(vehicle_per_order)
                                   if v not in shared_vid]
                rng.shuffle(non_shared_idxs)
                for i in non_shared_idxs[:need]:
                    vehicle_per_order[i] = vid

        TODAY = date(2026, 5, 17)
        order_count = 0
        payment_count = 0

        for order_date, vehicle_id in zip(all_dates, vehicle_per_order):
            scenario = rng.choice(SCENARIOS)
            mechanic_id = rng.choice(mech_ids)
            hour = rng.randint(9, 17)
            minute = rng.choice([0, 15, 30, 45])
            created_at = datetime(order_date.year, order_date.month,
                                  order_date.day, hour, minute)

            days_ago = (TODAY - order_date).days
            if days_ago > 30:
                status = rng.choices(["completed", "paid"], weights=[60, 40])[0]
            elif days_ago > 7:
                status = rng.choices(["completed", "paid", "ready_for_payment"],
                                     weights=[60, 25, 15])[0]
            else:
                status = rng.choices(["completed", "in_progress", "ready_for_payment", "new"],
                                     weights=[40, 30, 20, 10])[0]

            number = await _next_order_number(db)

            # Считаем total
            works_rows = []
            parts_rows = []
            total = Decimal("0")
            for w_name, base_price in scenario["works"]:
                price = Decimal(int(base_price * rng.uniform(0.95, 1.10) / 50) * 50)
                line = price  # qty=1, no discount
                total += line
                works_rows.append((w_name, 1, price, line))
            for p_name, article, base_price, qty in scenario["parts"]:
                price = Decimal(int(base_price * rng.uniform(0.98, 1.05) / 10) * 10)
                line = price * qty
                total += line
                parts_rows.append((p_name, article, qty, price, line))

            completed_at = None
            if status in ("completed", "paid"):
                completed_at = created_at + timedelta(hours=rng.randint(2, 8))

            mileage_at = rng.randint(15000, 200000)

            r = await db.execute(text(
                "INSERT INTO app.orders "
                "(tenant_id, number, vehicle_id, employee_id, mechanic_id, status, "
                " total_amount, paid_amount, mileage_at_service, comments, "
                " created_at, completed_at) "
                "VALUES (app.current_tenant(), :num, :vid, :eid, :mid, :st, "
                " :total, :paid, :km, :com, :cat, :compl) "
                "RETURNING id"
            ), {
                "num": number, "vid": vehicle_id, "eid": manager_id,
                "mid": mechanic_id if status != "new" else None,
                "st": status,
                "total": total,
                "paid": total if status == "paid" else Decimal("0"),
                "km": mileage_at,
                "com": scenario["comment"],
                "cat": created_at,
                "compl": completed_at,
            })
            order_id = r.scalar_one()

            for w_name, qty, price, line in works_rows:
                await db.execute(text(
                    "INSERT INTO app.order_works "
                    "(tenant_id, order_id, work_name, mechanic_id, quantity, price, discount, total) "
                    "VALUES (app.current_tenant(), :oid, :n, :mid, :q, :p, 0, :t)"
                ), {"oid": order_id, "n": w_name, "mid": mechanic_id,
                    "q": qty, "p": price, "t": line})

            for p_name, article, qty, price, line in parts_rows:
                await db.execute(text(
                    "INSERT INTO app.order_parts "
                    "(tenant_id, order_id, part_name, article, quantity, price, discount, total) "
                    "VALUES (app.current_tenant(), :oid, :n, :a, :q, :p, 0, :t)"
                ), {"oid": order_id, "n": p_name, "a": article,
                    "q": qty, "p": price, "t": line})

            if status == "paid":
                method = rng.choices(["cash", "card"], weights=[45, 55])[0]
                pay_ts = (completed_at or created_at) + timedelta(minutes=rng.randint(5, 90))
                await db.execute(text(
                    "INSERT INTO app.payments "
                    "(tenant_id, order_id, amount, payment_method, status, created_at) "
                    "VALUES (app.current_tenant(), :oid, :amt, :m, 'succeeded', :ts)"
                ), {"oid": order_id, "amt": total, "m": method, "ts": pay_ts})
                payment_count += 1

            order_count += 1

        # 5. Итоги
        print(f"\n  Создано клиентов:  {len(customer_ids)}")
        print(f"  Создано авто:      {len(vehicle_ids)}")
        print(f"  Создано заказов:   {order_count}")
        print(f"  Создано платежей:  {payment_count}")
        print(f"  Shared customers:  ids={customer_ids[:3]}")
        print(f"  Shared vehicles:   ids={vehicle_ids[:3]}")


def main():
    parser = argparse.ArgumentParser(description="Сид тестовых данных в тенант.")
    parser.add_argument("tenant_id", type=str, help="UUID тенанта")
    parser.add_argument("variant", nargs="?", choices=("a", "b"), default="a",
                        help="Какой пул уникальных клиентов использовать (default: a). "
                             "Shared-3 одинаковы в обоих вариантах.")
    args = parser.parse_args()

    try:
        tid = UUID(args.tenant_id)
    except ValueError:
        sys.exit(f"Некорректный tenant_id: {args.tenant_id!r}")

    asyncio.run(seed(tid, args.variant))


if __name__ == "__main__":
    main()
