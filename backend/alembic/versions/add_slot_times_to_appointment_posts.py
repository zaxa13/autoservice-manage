"""add slot_times to appointment_posts

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("appointment_posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slot_times", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appointment_posts", schema=None) as batch_op:
        batch_op.drop_column("slot_times")
