"""Сид недостающих брендов запчастей из таблицы качества

Сверка с пользовательской таблицей-классификатором брендов (хорошее
качество / с оговоркой / стоит воздержаться / неизвестно) — добавляем
~30 брендов, которых не хватало в исходном сиде 0010. Идемпотентно
через ON CONFLICT (name) DO NOTHING.

Revision ID: 0013_seed_more_part_brands
Revises: 0012_part_brands_insert_grant
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_seed_more_part_brands"
down_revision = "0012_part_brands_insert_grant"
branch_labels = None
depends_on = None


# Имена приведены к канону: акронимы — в верхнем регистре,
# полные слова — title case (как и большинство существующих записей).
NEW_BRANDS: list[str] = [
    "AD Russia",
    "AE",
    "Aisin",
    "Akitaka",
    "AMC",
    "A-One Parts",
    "Autowelt",
    "BJS",
    "Blue Print",
    "Clean",
    "Ctc",
    "Electrix",
    "GERI",
    "Glyco",
    "GTR",
    "H&K",
    "Hanse",
    "HDK",
    "HL Group",
    "Kager",
    "Kashiyama",
    "Kia",
    "KVB",
    "Lobro",
    "Mural",
    "RTS",
    "Sasic",
    "Seinsa",
    "SHAP",
    "Signav",
    "Tokico",
    "Walker",
]


def upgrade() -> None:
    # ON CONFLICT — на случай если часть имён случайно совпадёт с уже
    # сидированными (после расширения в будущем).
    for name in NEW_BRANDS:
        op.execute(
            sa.text("INSERT INTO app.part_brands(name) VALUES (:n) ON CONFLICT (name) DO NOTHING")
            .bindparams(n=name)
        )


def downgrade() -> None:
    for name in NEW_BRANDS:
        op.execute(
            sa.text("DELETE FROM app.part_brands WHERE name = :n").bindparams(n=name)
        )
