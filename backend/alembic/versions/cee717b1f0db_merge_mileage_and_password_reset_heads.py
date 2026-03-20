"""merge_mileage_and_password_reset_heads

Revision ID: cee717b1f0db
Revises: add_mileage_at_service, add_password_reset_tokens
Create Date: 2026-03-20 15:24:42.077261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cee717b1f0db'
down_revision = ('add_mileage_at_service', 'add_password_reset_tokens')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

