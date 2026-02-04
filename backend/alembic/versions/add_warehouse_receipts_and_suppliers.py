"""add warehouse receipts and suppliers

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("inn", sa.String(), nullable=True),
        sa.Column("contact", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("suppliers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_suppliers_id"), ["id"], unique=False)

    op.create_table(
        "receipt_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("receipt_documents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_receipt_documents_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_receipt_documents_number"), ["number"], unique=True)

    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipt_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("receipt_lines", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_receipt_lines_id"), ["id"], unique=False)

    with op.batch_alter_table("parts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("purchase_price_last", sa.Numeric(precision=10, scale=2), nullable=True))

    with op.batch_alter_table("warehouse_transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("receipt_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_warehouse_transactions_receipt_id",
            "receipt_documents",
            ["receipt_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("warehouse_transactions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_warehouse_transactions_receipt_id", type_="foreignkey")
        batch_op.drop_column("receipt_id")

    with op.batch_alter_table("parts", schema=None) as batch_op:
        batch_op.drop_column("purchase_price_last")

    op.drop_table("receipt_lines")
    op.drop_table("receipt_documents")
    op.drop_table("suppliers")
