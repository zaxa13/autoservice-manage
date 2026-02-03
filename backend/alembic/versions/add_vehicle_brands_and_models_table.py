"""add vehicle_brands and vehicle_models tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-01-31 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if 'vehicle_brands' not in tables:
        op.create_table('vehicle_brands',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('vehicle_brands', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_vehicle_brands_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_vehicle_brands_name'), ['name'], unique=True)

    if 'vehicle_models' not in tables:
        op.create_table('vehicle_models',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('brand_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.ForeignKeyConstraint(['brand_id'], ['vehicle_brands.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('vehicle_models', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_vehicle_models_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_vehicle_models_brand_id'), ['brand_id'], unique=False)


def downgrade() -> None:
    op.drop_table('vehicle_models')
    op.drop_table('vehicle_brands')
