"""add supplier bank and legal fields

Revision ID: d2e3f4a5b6c7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("suppliers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kpp", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("legal_address", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("bank_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("bik", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("bank_account", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("correspondent_account", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("suppliers", schema=None) as batch_op:
        batch_op.drop_column("correspondent_account")
        batch_op.drop_column("bank_account")
        batch_op.drop_column("bik")
        batch_op.drop_column("bank_name")
        batch_op.drop_column("legal_address")
        batch_op.drop_column("kpp")
