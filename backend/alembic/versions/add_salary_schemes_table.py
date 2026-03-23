"""add_salary_schemes_table

Revision ID: a1b2c3d4e5f6
Revises: 3e78f102e75d
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa

revision = 'aa11bb22cc33'
down_revision = '3e78f102e75d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'salary_schemes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('works_percentage', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('revenue_percentage', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id'),
    )
    op.create_index('ix_salary_schemes_id', 'salary_schemes', ['id'], unique=False)


def downgrade():
    op.drop_index('ix_salary_schemes_id', table_name='salary_schemes')
    op.drop_table('salary_schemes')
