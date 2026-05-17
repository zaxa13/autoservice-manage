"""SECURITY DEFINER функция app.sync_password_for_email

Используется platform-api при смене пароля владельцем в личном
кабинете (`/auth/change-password`, `/auth/reset-password`):
после UPDATE `platform.owners.password_hash` вызываем эту функцию,
чтобы синхронно обновить `app.users.password_hash` для admin-юзера
этого тенанта (email — глобально уникальный идентификатор).

Поведение:
- Возвращает `true`, если хотя бы одна строка обновлена.
- Возвращает `false`, если строки с таким email нет (например,
  владелец сменил пароль до того как provisioning успел создать
  admin user — это нормально, race window ~600 мс).

SECURITY DEFINER + REVOKE FROM PUBLIC + GRANT EXECUTE TO migrator_app
— platform-api ходит в app-DB под `migrator_app` ролью (см.
`tenant_provisioner.app_db_session`).

Revision ID: 0006_sync_password_for_email
Revises: 0005_seed_all_vehicle_models
Create Date: 2026-05-17
"""
from alembic import op


revision = "0006_sync_password_for_email"
down_revision = "0005_seed_all_vehicle_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.sync_password_for_email(
            p_email          text,
            p_password_hash  text
        )
        RETURNS boolean
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, app
        AS $$
        DECLARE
            v_rows integer;
        BEGIN
            UPDATE app.users
               SET password_hash = p_password_hash,
                   updated_at    = now()
             WHERE email = p_email;
            GET DIAGNOSTICS v_rows = ROW_COUNT;
            RETURN v_rows > 0;
        END;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "app.sync_password_for_email(text, text) FROM PUBLIC;"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION "
        "app.sync_password_for_email(text, text) TO migrator_app;"
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS "
        "app.sync_password_for_email(text, text);"
    )
