"""add recommendations and comments to orders

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-17 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поля recommendations и comments в таблицу orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recommendations', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('comments', sa.String(), nullable=True))


def downgrade() -> None:
    # Удаляем поля recommendations и comments из таблицы orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('comments')
        batch_op.drop_column('recommendations')
