"""initial schema for shared-DB tenant-app

Создаёт все бизнес-таблицы tenant-приложения в схеме `app` и включает
Row-Level Security для каждой:

    ALTER TABLE app.<t> ENABLE ROW LEVEL SECURITY;
    ALTER TABLE app.<t> FORCE  ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON app.<t>
      USING      (tenant_id = app.current_tenant())
      WITH CHECK (tenant_id = app.current_tenant());

`app.current_tenant()` (читает GUC `app.tenant_id`) и схемы `app` /
`platform`, и роли — должны быть созданы заранее bootstrap-скриптом
`infrastructure/db/init/01-init.sh` (на стороне platform-репо).

Миграция не выдаёт явных GRANT'ов: они приходят через
`ALTER DEFAULT PRIVILEGES`, настроенный в bootstrap для роли
`migrator_app` в схеме `app`.

Revision ID: 0001_shared_db_initial
Revises:
Create Date: 2026-05-09
"""
from alembic import op

from app.models._base import Base
from app.models import *  # noqa: F401,F403  регистрируем все таблицы в Base.metadata


revision = "0001_shared_db_initial"
down_revision = None
branch_labels = None
depends_on = None


def _app_table_names() -> list[str]:
    """Имена таблиц схемы `app` в порядке зависимостей."""
    return [t.name for t in Base.metadata.sorted_tables if t.schema == "app"]


def upgrade() -> None:
    bind = op.get_bind()

    # Sanity-check: схемы и helper-функция должны существовать (bootstrap).
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'app') THEN "
        "  RAISE EXCEPTION 'schema \"app\" not found — run infrastructure/db/init bootstrap first'; "
        "END IF; "
        "IF NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
        "               WHERE n.nspname='app' AND p.proname='current_tenant') THEN "
        "  RAISE EXCEPTION 'function app.current_tenant() not found — run bootstrap first'; "
        "END IF; "
        "END $$;"
    )

    # Создаём все таблицы (порядок зависимостей разрулит SQLAlchemy).
    Base.metadata.create_all(bind=bind)

    # Включаем RLS на всех бизнес-таблицах.
    # tenant_counters тоже под RLS — счётчик чужого тенанта читать/менять нельзя.
    for tbl in _app_table_names():
        op.execute(
            f"ALTER TABLE app.{tbl} ENABLE ROW LEVEL SECURITY;\n"
            f"ALTER TABLE app.{tbl} FORCE ROW LEVEL SECURITY;\n"
            f"CREATE POLICY tenant_isolation ON app.{tbl}\n"
            f"  USING      (tenant_id = app.current_tenant())\n"
            f"  WITH CHECK (tenant_id = app.current_tenant());"
        )


def downgrade() -> None:
    bind = op.get_bind()

    # Политики уйдут вместе с таблицами, но дропаем явно — детерминируемее.
    for tbl in reversed(_app_table_names()):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON app.{tbl};")

    Base.metadata.drop_all(bind=bind)
