"""Сид моделей для марки Audi (brands/audi.json, 77 моделей)

Записывает модели в app.vehicle_models, связывая их с уже существующей
маркой Audi (вставлена миграцией 0003). ON CONFLICT (brand_id, name)
DO NOTHING — идемпотентно при повторных прогонах.

Revision ID: 0004_seed_audi_models
Revises: 0003_global_vehicle_catalog
Create Date: 2026-05-16
"""
from alembic import op
from sqlalchemy import text


revision = "0004_seed_audi_models"
down_revision = "0003_global_vehicle_catalog"
branch_labels = None
depends_on = None


BRAND_NAME = "Audi"
MODELS: list[str] = [
    "50", "80", "90", "100", "200", "A1", "A2", "A3", "A4",
    "A4 allroad quattro", "A5", "A5L", "A6", "A6 allroad quattro",
    "A6 e-tron", "A7", "A8", "Cabriolet", "Coupe", "e-tron", "e-tron GT",
    "e-tron S", "e-tron Sportback", "e-tron Sportback S", "E5 Sportback",
    "E7X", "Q2", "Q2 e-tron", "Q3", "Q3 Sportback", "Q4 e-tron",
    "Q4 Sportback e-tron", "Q5", "Q5 e-tron", "Q5 Sportback", "Q6",
    "Q6 e-tron", "Q6 e-tron Sportback", "Q7", "Q8", "Q8 e-tron",
    "Q8 Sportback e-tron", "Quattro", "Quattro Sport", "R8", "RS e-tron GT",
    "RS Q3", "RS Q3 Sportback", "RS Q8", "RS2", "RS3", "RS4", "RS5",
    "RS6", "RS7", "S1", "S2", "S3", "S4", "S5", "S6", "S6 e-tron", "S7",
    "S8", "SQ2", "SQ5", "SQ5 Sportback", "SQ6 e-tron",
    "SQ6 e-tron Sportback", "SQ7", "SQ8", "SQ8 e-tron",
    "SQ8 Sportback e-tron", "TT", "TT RS", "TTS", "V8",
]


def upgrade() -> None:
    conn = op.get_bind()
    brand_id = conn.execute(
        text("SELECT id FROM app.vehicle_brands WHERE name = :name"),
        {"name": BRAND_NAME},
    ).scalar()
    if brand_id is None:
        raise RuntimeError(
            f"Бренд {BRAND_NAME!r} не найден — должна быть применена миграция 0003"
        )

    conn.execute(
        text(
            "INSERT INTO app.vehicle_models (brand_id, name) "
            "SELECT :b, m FROM unnest(CAST(:names AS text[])) AS t(m) "
            "ON CONFLICT (brand_id, name) DO NOTHING"
        ),
        {"b": brand_id, "names": MODELS},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "DELETE FROM app.vehicle_models "
            "WHERE brand_id = (SELECT id FROM app.vehicle_brands WHERE name = :name)"
        ),
        {"name": BRAND_NAME},
    )
