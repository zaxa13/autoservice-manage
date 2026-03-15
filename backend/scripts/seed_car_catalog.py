#!/usr/bin/env python3
"""
Скрипт для заполнения каталога марок и моделей автомобилей.
Содержит популярные в России марки и модели.
Использование: python scripts/seed_car_catalog.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.vehicle_brand import VehicleBrand, VehicleModel

# Каталог: марка -> список моделей
CAR_CATALOG = {
    "Lada (ВАЗ)": [
        "Granta", "Vesta", "XRAY", "Largus", "Niva Travel", "Niva Legend",
        "2107", "2106", "2105", "2104", "2103", "2101",
        "2109", "2110", "2111", "2112", "2114", "2115",
        "Kalina", "Priora", "Samara",
    ],
    "Toyota": [
        "Camry", "Corolla", "RAV4", "Land Cruiser", "Land Cruiser Prado",
        "Highlander", "Fortuner", "HiLux", "HiAce", "Avensis",
        "Auris", "Yaris", "Verso", "Prius", "CHR",
        "Venza", "Tundra", "Sequoia", "4Runner", "FJ Cruiser",
        "Alphard", "Crown", "Harrier",
    ],
    "Kia": [
        "Rio", "Ceed", "Sportage", "Sorento", "Cerato",
        "Optima", "Stinger", "Mohave", "Soul", "Seltos",
        "Carnival", "Telluride", "Picanto", "Stonic", "ProCeed",
        "XCeed", "EV6",
    ],
    "Hyundai": [
        "Solaris", "Elantra", "Tucson", "Santa Fe", "Creta",
        "i30", "i40", "Sonata", "Accent", "ix35",
        "Getz", "Matrix", "Veloster", "Palisade", "Venue",
        "Kona", "Ioniq", "NEXO", "Staria",
    ],
    "Volkswagen": [
        "Polo", "Golf", "Tiguan", "Passat", "Jetta",
        "Touareg", "Touran", "Sharan", "Caravelle", "Transporter",
        "Amarok", "Phaeton", "Arteon", "T-Roc", "T-Cross",
        "Taos", "Tayron", "Multivan",
    ],
    "Renault": [
        "Logan", "Sandero", "Duster", "Kaptur", "Arkana",
        "Megane", "Laguna", "Scenic", "Espace", "Koleos",
        "Fluence", "Symbol", "Clio", "Twingo", "Zoe",
        "Kangoo", "Master", "Trafic",
    ],
    "Nissan": [
        "Almera", "Tiida", "Teana", "X-Trail", "Qashqai",
        "Murano", "Pathfinder", "Patrol", "Navara", "Juke",
        "Note", "Micra", "Leaf", "370Z", "GT-R",
        "Kicks", "Terra", "Magnite",
    ],
    "BMW": [
        "1 серия", "2 серия", "3 серия", "4 серия", "5 серия",
        "6 серия", "7 серия", "8 серия",
        "X1", "X2", "X3", "X4", "X5", "X6", "X7",
        "Z4", "M3", "M5", "iX", "i4", "i7",
    ],
    "Mercedes-Benz": [
        "A-класс", "B-класс", "C-класс", "E-класс", "S-класс",
        "CLA", "CLS", "GLA", "GLB", "GLC", "GLE", "GLS",
        "G-класс", "V-класс", "Vito", "Sprinter",
        "AMG GT", "SL", "EQC", "EQS",
    ],
    "Audi": [
        "A1", "A3", "A4", "A5", "A6", "A7", "A8",
        "Q2", "Q3", "Q5", "Q7", "Q8",
        "TT", "R8", "e-tron", "e-tron GT",
        "S3", "S4", "S5", "S6", "RS3", "RS6",
    ],
    "Ford": [
        "Focus", "Mondeo", "Fiesta", "Fusion", "Explorer",
        "Edge", "Kuga", "EcoSport", "Mustang", "F-150",
        "Transit", "Ranger", "Galaxy", "S-Max",
        "Puma", "Bronco",
    ],
    "Mazda": [
        "Mazda3", "Mazda6", "CX-3", "CX-5", "CX-7",
        "CX-9", "CX-30", "CX-50", "CX-60",
        "MX-5", "MX-30", "BT-50",
        "Mazda2", "Demio",
    ],
    "Mitsubishi": [
        "Lancer", "Outlander", "ASX", "Eclipse Cross",
        "Pajero", "Pajero Sport", "L200",
        "Galant", "Carisma", "Colt",
        "Grandis", "i-MiEV",
    ],
    "Skoda": [
        "Octavia", "Fabia", "Superb", "Rapid",
        "Kodiaq", "Karoq", "Kamiq", "Enyaq",
        "Scala", "Roomster", "Yeti",
    ],
    "Honda": [
        "Civic", "Accord", "CR-V", "HR-V", "Pilot",
        "Jazz", "Fit", "Freed", "Odyssey",
        "Ridgeline", "e:Ny1", "ZR-V",
        "Legend", "Insight",
    ],
    "Chevrolet": [
        "Cruze", "Aveo", "Captiva", "Epica", "Lacetti",
        "Orlando", "Spark", "Cobalt", "Niva",
        "Tahoe", "Suburban", "Malibu", "Camaro", "Corvette",
        "Silverado", "Equinox", "Trailblazer",
    ],
    "Opel": [
        "Astra", "Vectra", "Zafira", "Insignia", "Antara",
        "Mokka", "Corsa", "Meriva", "Omega",
        "Frontera", "Vivaro", "Movano",
    ],
    "Peugeot": [
        "206", "207", "208", "301", "307", "308",
        "405", "406", "407", "408", "508",
        "2008", "3008", "4008", "5008",
        "Partner", "Expert", "Boxer",
    ],
    "Citroën": [
        "C1", "C2", "C3", "C4", "C5", "C6",
        "C3 Aircross", "C4 Cactus", "C5 Aircross",
        "Berlingo", "Jumpy", "Jumper",
        "Xsara", "Saxo", "Picasso",
    ],
    "Lexus": [
        "IS", "ES", "GS", "LS", "GX", "LX",
        "NX", "RX", "UX", "TX",
        "RC", "LC", "CT",
    ],
    "Land Rover": [
        "Defender", "Discovery", "Discovery Sport",
        "Range Rover", "Range Rover Sport", "Range Rover Evoque",
        "Range Rover Velar", "Freelander",
    ],
    "Volvo": [
        "S40", "S60", "S80", "S90",
        "V40", "V60", "V70", "V90",
        "XC40", "XC60", "XC70", "XC90",
        "C30", "C70",
    ],
    "Subaru": [
        "Impreza", "Legacy", "Outback", "Forester",
        "XV", "Tribeca", "BRZ",
        "WRX", "WRX STI", "Levorg",
        "Crosstrek", "Ascent",
    ],
    "Suzuki": [
        "SX4", "Swift", "Grand Vitara", "Jimny",
        "Vitara", "Baleno", "Ignis", "S-Cross",
        "Liana", "Alto", "Wagon R",
    ],
    "Geely": [
        "Atlas", "Atlas Pro", "Coolray", "Tugella",
        "Monjaro", "Emgrand", "GC6",
        "Okavango", "Preface",
    ],
    "Haval": [
        "F7", "F7x", "H6", "H9",
        "Jolion", "Dargo", "Poer",
    ],
    "Chery": [
        "Tiggo 4", "Tiggo 7", "Tiggo 7 Pro", "Tiggo 8", "Tiggo 8 Pro",
        "Arrizo 5", "Arrizo 8",
        "QQ", "Amulet", "Fora",
    ],
    "УАЗ": [
        "Патриот", "Хантер", "Буханка", "Пикап",
        "3151", "3303", "469",
    ],
    "ГАЗ": [
        "Газель Next", "Газель Business", "Газель 3302",
        "Соболь", "ГАЗон Next", "Валдай",
        "31105", "3110", "Волга Сайбер",
    ],
    "Infiniti": [
        "Q30", "Q50", "Q60", "Q70",
        "QX30", "QX50", "QX55", "QX60", "QX70", "QX80",
        "G35", "G37", "FX35", "FX37",
    ],
    "Porsche": [
        "911", "Cayenne", "Macan", "Panamera",
        "Taycan", "Cayman", "Boxster",
    ],
    "Jeep": [
        "Wrangler", "Cherokee", "Grand Cherokee",
        "Renegade", "Compass", "Gladiator",
        "Grand Wagoneer",
    ],
    "Seat": [
        "Ibiza", "Leon", "Ateca", "Tarraco",
        "Toledo", "Arona", "Mii",
    ],
    "Fiat": [
        "Punto", "Bravo", "Doblo", "Ducato",
        "500", "Tipo", "Panda", "Freemont",
    ],
    "Datsun": [
        "on-DO", "mi-DO",
    ],
    "LADA": [  # Дубль для совместимости — пропускается если уже есть Lada
        # пустой, будет пропущен
    ],
    "Exeed": [
        "TXL", "VX", "TX", "LX", "RX",
    ],
    "Omoda": [
        "C5",
    ],
    "Jaecoo": [
        "J7",
    ],
    "Jetour": [
        "X70", "X90", "Dashing",
    ],
    "BAIC": [
        "X35", "X55", "X75", "BJ40",
    ],
    "Dongfeng": [
        "AX7", "AX4", "DFSK Glory",
    ],
    "JAC": [
        "S3", "S4", "S7", "J7", "T6", "T8",
    ],
    "Isuzu": [
        "D-Max", "MU-X", "Trooper", "Bighorn",
    ],
    "Acura": [
        "MDX", "RDX", "TLX", "ILX", "NSX",
    ],
    "Alfa Romeo": [
        "156", "159", "166", "147",
        "Giulia", "Giulietta", "Stelvio",
    ],
    "Dacia": [
        "Logan", "Sandero", "Duster", "Lodgy", "Dokker",
    ],
    "Daewoo": [
        "Nexia", "Matiz", "Lanos", "Nubira",
        "Lacetti", "Magnus", "Kalos",
    ],
    "SsangYong": [
        "Rexton", "Actyon", "Kyron", "Korando",
        "Tivoli", "Musso",
    ],
    "Cadillac": [
        "Escalade", "XT5", "XT6", "CT6", "ATS", "CTS",
    ],
    "Pontiac": [
        "Grand Prix", "Firebird", "Trans Am",
    ],
}


def seed_car_catalog():
    db = SessionLocal()
    try:
        existing_brands = db.query(VehicleBrand).count()
        if existing_brands > 0:
            print(f"⚠️  В базе уже есть {existing_brands} марок.")
            answer = input("Добавить недостающие марки/модели? (y/n): ").strip().lower()
            if answer != "y":
                print("Отменено.")
                return

        total_brands = 0
        total_models = 0
        skipped_brands = 0
        skipped_models = 0

        for brand_name, models in CAR_CATALOG.items():
            if not models:
                continue

            # Ищем или создаём марку
            brand = db.query(VehicleBrand).filter(VehicleBrand.name == brand_name).first()
            if not brand:
                brand = VehicleBrand(name=brand_name)
                db.add(brand)
                db.flush()
                total_brands += 1
                print(f"  + Марка: {brand_name}")
            else:
                skipped_brands += 1

            # Добавляем модели
            existing_model_names = {
                m.name for m in db.query(VehicleModel).filter(VehicleModel.brand_id == brand.id).all()
            }

            for model_name in models:
                if model_name in existing_model_names:
                    skipped_models += 1
                    continue
                model = VehicleModel(brand_id=brand.id, name=model_name)
                db.add(model)
                total_models += 1

        db.commit()

        print()
        print("=" * 50)
        print("✅ Каталог успешно загружен!")
        print(f"   Добавлено марок:  {total_brands}")
        print(f"   Добавлено моделей: {total_models}")
        if skipped_brands or skipped_models:
            print(f"   Пропущено марок:  {skipped_brands} (уже были)")
            print(f"   Пропущено моделей: {skipped_models} (уже были)")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_car_catalog()
