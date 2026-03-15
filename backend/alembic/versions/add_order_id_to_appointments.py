"""add order_id to appointments

Revision ID: f1a2b3c4d5e6
Revises: add_slot_times_to_appointment_posts
Branch Labels: None
Depends On: None

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'g5h6i7j8k9l0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    columns = [c['name'] for c in inspector.get_columns('appointments')]
    if 'order_id' not in columns:
        with op.batch_alter_table('appointments', schema=None) as batch_op:
            batch_op.add_column(sa.Column('order_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_appointments_order_id',
                'orders',
                ['order_id'],
                ['id'],
            )


def downgrade() -> None:
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_appointments_order_id', type_='foreignkey')
        batch_op.drop_column('order_id')
