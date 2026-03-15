"""add settings table

Revision ID: add_settings_table
Revises: add_slot_times_to_appointment_posts
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_settings_table'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'settings',
        sa.Column('key', sa.String(), primary_key=True, index=True),
        sa.Column('value', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('settings')
