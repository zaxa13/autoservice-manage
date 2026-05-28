"""perf-индексы для агрегаций дашборда и фильтрации списка заказов

- orders(tenant_id, completed_at) — нужен агрегациям выручки по закрытым ЗН
  (_completed_revenue_range в dashboard.py) и фильтру отчётов по дате
  закрытия. Сейчас нет — на 10k+ строк план уйдёт в seq scan.
- payments(tenant_id, created_at) — нужен агрегациям поступлений
  (_revenue_range, _revenue_by_day, _revenue_by_month). Сейчас есть только
  (tenant_id, order_id) — для аналитики бесполезен.

Индексы создаются IF NOT EXISTS чтобы миграция была идемпотентна и не падала,
если их ручную накатили заранее.

Revision ID: 0009_perf_indexes
Revises: 0008_payment_logs
Create Date: 2026-05-28
"""
from alembic import op


revision = "0009_perf_indexes"
down_revision = "0008_payment_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_orders_tenant_completed_at "
        "ON app.orders (tenant_id, completed_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_payments_tenant_created_at "
        "ON app.payments (tenant_id, created_at);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_payments_tenant_created_at;")
    op.execute("DROP INDEX IF EXISTS app.ix_orders_tenant_completed_at;")
