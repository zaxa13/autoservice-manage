"""tenant_app получает INSERT на part_brands

Чтобы любой пользователь приложения мог добавлять отсутствующие бренды
прямо из карточки запчасти, расширяем права tenant_app на app.part_brands
до INSERT (раньше было только SELECT по 0010). UPDATE/DELETE по-прежнему
запрещены — каталог append-only из приложения.

Revision ID: 0012_part_brands_insert_grant
Revises: 0011_seed_oem_part_brands
Create Date: 2026-05-29
"""
from alembic import op


revision = "0012_part_brands_insert_grant"
down_revision = "0011_seed_oem_part_brands"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT INSERT ON app.part_brands TO tenant_app;")


def downgrade() -> None:
    op.execute("REVOKE INSERT ON app.part_brands FROM tenant_app;")
