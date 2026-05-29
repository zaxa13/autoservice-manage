"""Сид OEM-брендов запчастей на основе vehicle_brands

Для каждой марки авто в каталоге vehicle_brands добавляем запись вида
«{марка} OEM» в part_brands, чтобы пользователь мог выбирать
оригинальные запчасти производителя автомобиля. Идемпотентно: при
повторном накате конфликты по UNIQUE(name) игнорируются — это нужно,
если в будущем в vehicle_brands добавят новые марки и придётся
повторить сид.

Revision ID: 0011_seed_oem_part_brands
Revises: 0010_part_brands_catalog
Create Date: 2026-05-29
"""
from alembic import op


revision = "0011_seed_oem_part_brands"
down_revision = "0010_part_brands_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO app.part_brands(name)
        SELECT name || ' OEM'
        FROM app.vehicle_brands
        ON CONFLICT (name) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Удаляем только OEM-записи, оставляя «обычные» бренды нетронутыми.
    op.execute("DELETE FROM app.part_brands WHERE name LIKE '% OEM';")
