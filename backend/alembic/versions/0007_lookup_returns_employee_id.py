"""lookup_user_for_login: добавить employee_id в результат

`/auth/login` сейчас читает только (user_id, tenant_id, password_hash,
role, is_active). Без employee_id JWT не может содержать `employee_id`
claim, а без него рейсты вроде POST /orders/ возвращают 400
("JWT-токен не содержит employee_id"). Расширяем функцию и контракт.

Replace, не drop+create — функция возвращает TABLE, поэтому меняется
сигнатура → нужен `CREATE OR REPLACE` с новым `RETURNS TABLE`.
Postgres такое не разрешает (only same return type for CREATE OR
REPLACE), поэтому сначала DROP, потом CREATE.

Revision ID: 0007_lookup_returns_employee_id
Revises: 0006_sync_password_for_email
Create Date: 2026-05-17
"""
from alembic import op


revision = "0007_lookup_returns_employee_id"
down_revision = "0006_sync_password_for_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.lookup_user_for_login(text);")
    op.execute(
        """
        CREATE FUNCTION app.lookup_user_for_login(p_email text)
        RETURNS TABLE (
            user_id        bigint,
            tenant_id      uuid,
            password_hash  text,
            role           text,
            is_active      boolean,
            employee_id    bigint
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = pg_catalog, app
        AS $$
            SELECT id, tenant_id, password_hash, role, is_active, employee_id
            FROM app.users
            WHERE email = p_email
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app.lookup_user_for_login(text) FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION app.lookup_user_for_login(text) TO tenant_app;")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.lookup_user_for_login(text);")
    op.execute(
        """
        CREATE FUNCTION app.lookup_user_for_login(p_email text)
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
    op.execute("REVOKE ALL ON FUNCTION app.lookup_user_for_login(text) FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION app.lookup_user_for_login(text) TO tenant_app;")
