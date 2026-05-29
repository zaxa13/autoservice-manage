"""Сид брендов из второй разборной статьи drive2

После сверки с дополнительной публикацией добавляем 26 брендов,
которых ещё нет в каталоге. Идемпотентно через ON CONFLICT DO NOTHING.

Revision ID: 0014_seed_more_part_brands_v2
Revises: 0013_seed_more_part_brands
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_seed_more_part_brands_v2"
down_revision = "0013_seed_more_part_brands"
branch_labels = None
depends_on = None


NEW_BRANDS: list[str] = [
    "Akyoto",
    "Borshung",
    "Brisk",
    "Corteco",
    "Exedy",
    "Krauf",
    "Liqui Moly",
    "Luzar",
    "Metzger",
    "Mopar",
    "Morse Friction",
    "Motorherz",
    "MV-Parts",
    "Nachi",
    "National",
    "Nippon Pieces",
    "Nisshinbo",
    "NTP",
    "Polmostrow",
    "Raybestos",
    "Stellox",
    "Sumitomo",
    "Timken",
    "VTR",
    "Zaufer",
    "ХОРС",
]


def upgrade() -> None:
    for name in NEW_BRANDS:
        op.execute(
            sa.text(
                "INSERT INTO app.part_brands(name) VALUES (:n) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(n=name)
        )


def downgrade() -> None:
    for name in NEW_BRANDS:
        op.execute(
            sa.text("DELETE FROM app.part_brands WHERE name = :n").bindparams(n=name)
        )
