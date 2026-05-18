"""payment_logs: append-only audit таблица для платежей

Каждое создание/отмена платежа пишет снимок состояния в payment_logs.
Колонки мирят payments + own id + payment_id + employee_id (актор).

Revision ID: 0008_payment_logs
Revises: 0007_lookup_returns_employee_id
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


revision = "0008_payment_logs"
down_revision = "0007_lookup_returns_employee_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_logs",
        sa.Column("tenant_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("yookassa_payment_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["app.payments.tenant_id", "app.payments.id"],
            ondelete="CASCADE",
            name="fk_payment_logs_payment",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["app.orders.tenant_id", "app.orders.id"],
            ondelete="CASCADE",
            name="fk_payment_logs_order",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["app.employees.tenant_id", "app.employees.id"],
            ondelete="SET NULL",
            name="fk_payment_logs_employee",
        ),
        schema="app",
    )
    op.create_index(
        "ix_payment_logs_tenant_payment",
        "payment_logs",
        ["tenant_id", "payment_id"],
        schema="app",
    )
    op.create_index(
        "ix_payment_logs_tenant_order",
        "payment_logs",
        ["tenant_id", "order_id"],
        schema="app",
    )

    # RLS — по такой же политике как остальные tenant-таблицы.
    op.execute(
        "ALTER TABLE app.payment_logs ENABLE ROW LEVEL SECURITY;\n"
        "ALTER TABLE app.payment_logs FORCE ROW LEVEL SECURITY;\n"
        "CREATE POLICY tenant_isolation ON app.payment_logs\n"
        "  USING      (tenant_id = app.current_tenant())\n"
        "  WITH CHECK (tenant_id = app.current_tenant());"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON app.payment_logs;")
    op.drop_index("ix_payment_logs_tenant_order", table_name="payment_logs", schema="app")
    op.drop_index("ix_payment_logs_tenant_payment", table_name="payment_logs", schema="app")
    op.drop_table("payment_logs", schema="app")
