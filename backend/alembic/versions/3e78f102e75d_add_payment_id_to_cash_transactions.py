"""add_payment_id_to_cash_transactions

Revision ID: 3e78f102e75d
Revises: 0cba7978c227
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa

revision = '3e78f102e75d'
down_revision = '0cba7978c227'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('cash_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_cash_transactions_payment_id',
            'payments', ['payment_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('cash_transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cash_transactions_payment_id', type_='foreignkey')
        batch_op.drop_column('payment_id')
