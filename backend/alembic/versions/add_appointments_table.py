"""add appointments table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование таблицы appointments перед созданием
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Создаем таблицу appointments только если её еще нет
    if 'appointments' not in tables:
        op.create_table('appointments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('time', sa.Time(), nullable=False),
            sa.Column('customer_name', sa.String(), nullable=False),
            sa.Column('customer_phone', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('vehicle_id', sa.Integer(), nullable=True),
            sa.Column('employee_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
            sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], )
        )
        with op.batch_alter_table('appointments', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_appointments_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_appointments_date'), ['date'], unique=False)


def downgrade() -> None:
    # Удаляем таблицу appointments
    op.drop_table('appointments')
