"""add password_reset_tokens table

Revision ID: add_password_reset_tokens
Revises: add_settings_table
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_password_reset_tokens'
down_revision = 'caf439a50356'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(), unique=True, index=True, nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('password_reset_tokens')
