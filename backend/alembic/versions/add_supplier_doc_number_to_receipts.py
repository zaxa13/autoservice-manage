"""add supplier document number to receipts

Revision ID: d1e2f3a4b5c6
Revises: d0e1f2a3b4c5
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("receipt_documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("supplier_document_number", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("supplier_document_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("receipt_documents", schema=None) as batch_op:
        batch_op.drop_column("supplier_document_date")
        batch_op.drop_column("supplier_document_number")

