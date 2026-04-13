"""update order statuses

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Обновляем старые статусы 'completed' на 'ready_for_payment'
    op.execute("""
        UPDATE orders
        SET status = 'ready_for_payment'
        WHERE status::text = 'completed' OR status::text = 'COMPLETED'
    """)


def downgrade() -> None:
    # Возвращаем 'ready_for_payment' обратно в 'completed' (старая версия)
    op.execute("""
        UPDATE orders 
        SET status = 'completed' 
        WHERE status = 'ready_for_payment'
    """)
