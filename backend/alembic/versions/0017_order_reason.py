"""orders.reason: причина обращения (со слов клиента)

Необязательное свободное текстовое поле, заполняется при создании заказ-наряда
и выводится в печатную форму (шаблон order.html, блок «Причина обращения»).

Revision ID: 0017_order_reason
Revises: 0016_user_sessions
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_order_reason"
down_revision = "0016_user_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("reason", sa.String(2000), nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("orders", "reason", schema="app")
