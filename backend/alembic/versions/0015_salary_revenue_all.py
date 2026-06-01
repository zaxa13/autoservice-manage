"""Флаг revenue_all_orders для схемы зарплаты менеджера

Менеджер может настроиться на бонус «по всем закрытым заказам» (а не только
по тем, где он указан ответственным). Полезно для маленьких автосервисов,
где заказы могут закрывать админы / коллеги, но бонус должен оставаться у
ответственного менеджера-смены.

Revision ID: 0015_salary_revenue_all
Revises: 0014_seed_more_part_brands_v2
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_salary_revenue_all"
down_revision = "0014_seed_more_part_brands_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "salary_schemes",
        sa.Column(
            "revenue_all_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("salary_schemes", "revenue_all_orders", schema="app")
