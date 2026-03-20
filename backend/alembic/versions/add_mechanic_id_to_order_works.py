"""add mechanic_id to order_works

Revision ID: add_mechanic_id_to_order_works
Revises: cee717b1f0db
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_mechanic_id_to_order_works'
down_revision = 'cee717b1f0db'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order_works', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mechanic_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_order_works_mechanic_id',
            'employees',
            ['mechanic_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('order_works', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_works_mechanic_id', type_='foreignkey')
        batch_op.drop_column('mechanic_id')
