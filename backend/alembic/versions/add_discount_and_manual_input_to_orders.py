"""add discount and manual input fields to order works and parts

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Обновляем таблицу order_works
    with op.batch_alter_table('order_works', schema=None) as batch_op:
        # Делаем work_id nullable для возможности ручного ввода
        batch_op.alter_column('work_id', nullable=True)
        # Добавляем discount
        batch_op.add_column(sa.Column('discount', sa.Numeric(10, 2), nullable=True, server_default=sa.text('0')))
        # Добавляем work_name для ручного ввода
        batch_op.add_column(sa.Column('work_name', sa.String(), nullable=True))

    # Обновляем таблицу order_parts
    with op.batch_alter_table('order_parts', schema=None) as batch_op:
        # Делаем part_id nullable для возможности ручного ввода
        batch_op.alter_column('part_id', nullable=True)
        # Добавляем discount
        batch_op.add_column(sa.Column('discount', sa.Numeric(10, 2), nullable=True, server_default=sa.text('0')))
        # Добавляем article для артикула запчасти
        batch_op.add_column(sa.Column('article', sa.String(), nullable=True))
        # Добавляем part_name для ручного ввода
        batch_op.add_column(sa.Column('part_name', sa.String(), nullable=True))


def downgrade() -> None:
    # Откатываем изменения в order_parts
    with op.batch_alter_table('order_parts', schema=None) as batch_op:
        batch_op.drop_column('part_name')
        batch_op.drop_column('article')
        batch_op.drop_column('discount')
        batch_op.alter_column('part_id', nullable=False)

    # Откатываем изменения в order_works
    with op.batch_alter_table('order_works', schema=None) as batch_op:
        batch_op.drop_column('work_name')
        batch_op.drop_column('discount')
        batch_op.alter_column('work_id', nullable=False)
