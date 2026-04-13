"""fix_enum_values_to_lowercase

Revision ID: caf439a50356
Revises: add_settings_table
Create Date: 2026-03-09 11:59:05.181179

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'caf439a50356'
down_revision = 'add_settings_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert all uppercase enum values to lowercase in the database
    # This migration fixes data that was created with uppercase enum values
    # when the models expect lowercase values
    
    # Update parts.category
    op.execute("""
        UPDATE parts
        SET category = LOWER(category::text)::partcategory
        WHERE category::text != LOWER(category::text)
    """)

    # Update works.category
    op.execute("""
        UPDATE works
        SET category = LOWER(category::text)::workcategory
        WHERE category::text != LOWER(category::text)
    """)

    # Update employees.position
    op.execute("""
        UPDATE employees
        SET position = LOWER(position::text)::employeeposition
        WHERE position::text != LOWER(position::text)
    """)

    # Update users.role
    op.execute("""
        UPDATE users
        SET role = LOWER(role::text)::userrole
        WHERE role::text != LOWER(role::text)
    """)

    # Update warehouse_transactions.transaction_type
    op.execute("""
        UPDATE warehouse_transactions
        SET transaction_type = LOWER(transaction_type::text)::transactiontype
        WHERE transaction_type::text != LOWER(transaction_type::text)
    """)


def downgrade() -> None:
    # Revert to uppercase enum values (for rollback purposes)
    
    # Update parts.category
    op.execute("""
        UPDATE parts
        SET category = UPPER(category::text)::partcategory
        WHERE category::text = 'other'
    """)
    
    # Note: We only revert 'other' to 'OTHER' as that was the problematic one
    # Other enum values were consistently lowercase in the seed data

