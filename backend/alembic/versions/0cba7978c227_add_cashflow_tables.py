"""add_cashflow_tables

Revision ID: 0cba7978c227
Revises: add_mechanic_id_to_order_works
Create Date: 2026-03-20 21:09:14.256508

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cba7978c227'
down_revision = 'add_mechanic_id_to_order_works'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cash_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('initial_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cash_accounts_id', 'cash_accounts', ['id'], unique=False)

    op.create_table(
        'cash_transaction_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cash_transaction_categories_id', 'cash_transaction_categories', ['id'], unique=False)

    op.create_table(
        'cash_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('to_account_id', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('salary_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['cash_accounts.id']),
        sa.ForeignKeyConstraint(['category_id'], ['cash_transaction_categories.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['salary_id'], ['salaries.id']),
        sa.ForeignKeyConstraint(['to_account_id'], ['cash_accounts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cash_transactions_id', 'cash_transactions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_cash_transactions_id', table_name='cash_transactions')
    op.drop_table('cash_transactions')
    op.drop_index('ix_cash_transaction_categories_id', table_name='cash_transaction_categories')
    op.drop_table('cash_transaction_categories')
    op.drop_index('ix_cash_accounts_id', table_name='cash_accounts')
    op.drop_table('cash_accounts')
