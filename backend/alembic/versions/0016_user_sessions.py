"""user_sessions: учёт активных сессий тенанта (лимит по тарифу)

Seat-based лимит: число одновременно активных сессий на ВЕСЬ тенант
ограничено по тарифу (platform.tariff_plans.limits->>'max_sessions').
«Активная» = revoked_at IS NULL AND expires_at > now() AND last_seen_at
свежий (idle-окно). Закрытая вкладка освобождает место лениво по idle.

Revision ID: 0016_user_sessions
Revises: 0015_salary_revenue_all
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


revision = "0016_user_sessions"
down_revision = "0015_salary_revenue_all"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("tenant_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        # jti — идентификатор сессии, кладётся в JWT; по нему logout/touch.
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("login_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(40), nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["app.users.tenant_id", "app.users.id"],
            ondelete="CASCADE",
            name="fk_user_sessions_user",
        ),
        sa.UniqueConstraint("tenant_id", "jti", name="uq_user_sessions_tenant_jti"),
        schema="app",
    )
    # Индекс под подсчёт активных сессий (RLS уже отфильтрует по tenant_id).
    op.create_index(
        "ix_user_sessions_active",
        "user_sessions",
        ["tenant_id", "last_seen_at"],
        schema="app",
    )

    # RLS — как у остальных tenant-таблиц.
    op.execute(
        "ALTER TABLE app.user_sessions ENABLE ROW LEVEL SECURITY;\n"
        "ALTER TABLE app.user_sessions FORCE ROW LEVEL SECURITY;\n"
        "CREATE POLICY tenant_isolation ON app.user_sessions\n"
        "  USING      (tenant_id = app.current_tenant())\n"
        "  WITH CHECK (tenant_id = app.current_tenant());"
    )
    # Рантайм-роль: SELECT/INSERT/UPDATE (DELETE не нужен — чистим по expiry/cron).
    op.execute("GRANT SELECT, INSERT, UPDATE ON app.user_sessions TO tenant_app;")


def downgrade() -> None:
    op.execute("REVOKE ALL ON app.user_sessions FROM tenant_app;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON app.user_sessions;")
    op.drop_index("ix_user_sessions_active", table_name="user_sessions", schema="app")
    op.drop_table("user_sessions", schema="app")
