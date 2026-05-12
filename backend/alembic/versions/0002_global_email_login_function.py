"""global unique email + lookup_user_for_login function

В Phase 7 multi-tenant per email явно отрезан: каждый клиент =
свой owner = свой tenant, email — глобальный identity.

Что делает миграция:
1. Дропает `uq_users_tenant_email` (был unique по (tenant_id, email)).
2. Добавляет `uq_users_email_global` — UNIQUE(email).
3. Создаёт `app.lookup_user_for_login(p_email text)` — SECURITY DEFINER
   функция. Возвращает (user_id, tenant_id, password_hash, role,
   is_active) для одного email. SECURITY DEFINER нужен, чтобы прыгнуть
   через RLS на `app.users`: на login-эндпоинте мы ещё не знаем
   tenant_id, поэтому обычный tenant_app не сможет читать users
   (там FORCE ROW LEVEL SECURITY).
4. Жёстко закрывает search_path и REVOKE FROM PUBLIC, GRANT EXECUTE
   только роли `tenant_app` — только она вызывает функцию из
   runtime-кода.

Revision ID: 0002_global_email_login_function
Revises: 0001_shared_db_initial
Create Date: 2026-05-12
"""
from alembic import op


revision = "0002_global_email_login_function"
down_revision = "0001_shared_db_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. drop per-tenant unique on email
    op.execute("ALTER TABLE app.users DROP CONSTRAINT IF EXISTS uq_users_tenant_email;")

    # 2. global unique on email
    # Если в БД остались дубли (например, от smoke-регистраций до Phase 7),
    # эта команда упадёт — это правильное поведение, разбираемся вручную.
    op.execute(
        "ALTER TABLE app.users "
        "ADD CONSTRAINT uq_users_email_global UNIQUE (email);"
    )

    # 3. SECURITY DEFINER lookup function.
    # Owner функции = роль, которая выполняет миграцию (`migrator_app`,
    # BYPASSRLS). При вызове SECURITY DEFINER исполняется с её правами →
    # bypass RLS на app.users.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.lookup_user_for_login(p_email text)
        RETURNS TABLE (
            user_id        bigint,
            tenant_id      uuid,
            password_hash  text,
            role           text,
            is_active      boolean
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = pg_catalog, app
        AS $$
            SELECT id, tenant_id, password_hash, role, is_active
            FROM app.users
            WHERE email = p_email
        $$;
        """
    )

    # 4. Только tenant_app может звать функцию (runtime role).
    op.execute("REVOKE ALL ON FUNCTION app.lookup_user_for_login(text) FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION app.lookup_user_for_login(text) TO tenant_app;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.lookup_user_for_login(text);")
    op.execute("ALTER TABLE app.users DROP CONSTRAINT IF EXISTS uq_users_email_global;")
    op.execute(
        "ALTER TABLE app.users "
        "ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email);"
    )
