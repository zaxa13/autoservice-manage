"""add appointment_posts table and post_id/sort_order to appointments

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointment_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("max_slots", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("appointment_posts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_appointment_posts_id"), ["id"], unique=False)

    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("post_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key("fk_appointments_post_id", "appointment_posts", ["post_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_appointments_post_id", type_="foreignkey")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("post_id")
    op.drop_table("appointment_posts")
