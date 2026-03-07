"""add status to appointments

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa


revision = "g5h6i7j8k9l0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=50), nullable=True))

    op.execute("UPDATE appointments SET status = 'scheduled' WHERE status IS NULL")

    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.alter_column("status", nullable=False, server_default="scheduled")


def downgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_column("status")
