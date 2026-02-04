"""parts.part_number NOT NULL — артикул обязателен

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Заполняем NULL/пустые артикулы временным значением (ART_<id>), чтобы можно было выставить NOT NULL
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE parts SET part_number = 'ART' || id WHERE part_number IS NULL OR part_number = ''"))
    with op.batch_alter_table("parts", schema=None) as batch_op:
        batch_op.alter_column(
            "part_number",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("parts", schema=None) as batch_op:
        batch_op.alter_column(
            "part_number",
            existing_type=sa.String(),
            nullable=True,
        )
