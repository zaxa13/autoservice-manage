"""add mileage_at_service to orders

Revision ID: add_mileage_at_service
Revises: caf439a50356
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_mileage_at_service'
down_revision = 'caf439a50356'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mileage_at_service', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('mileage_at_service')
