"""fix_paymentstatus_enum_to_lowercase

Revision ID: fix_paymentstatus_lowercase
Revises: aa11bb22cc33
Create Date: 2026-04-17 19:30:00.000000

The initial migration created the paymentstatus PostgreSQL enum type with
UPPERCASE values ('PENDING', 'SUCCEEDED', etc.), while the Python model uses
lowercase. This migration recreates the enum with lowercase values and migrates
existing data.
"""
from alembic import op
import sqlalchemy as sa


revision = 'fix_paymentstatus_lowercase'
down_revision = 'aa11bb22cc33'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum type with lowercase values
    op.execute("CREATE TYPE paymentstatus_new AS ENUM ('pending', 'succeeded', 'cancelled', 'refunded')")

    # Migrate column to new type, converting existing data to lowercase
    op.execute("""
        ALTER TABLE payments
        ALTER COLUMN status TYPE paymentstatus_new
        USING LOWER(status::text)::paymentstatus_new
    """)

    # Drop old type
    op.execute("DROP TYPE paymentstatus")

    # Rename new type to original name
    op.execute("ALTER TYPE paymentstatus_new RENAME TO paymentstatus")


def downgrade() -> None:
    # Recreate uppercase enum type
    op.execute("CREATE TYPE paymentstatus_old AS ENUM ('PENDING', 'SUCCEEDED', 'CANCELLED', 'REFUNDED')")

    op.execute("""
        ALTER TABLE payments
        ALTER COLUMN status TYPE paymentstatus_old
        USING UPPER(status::text)::paymentstatus_old
    """)

    op.execute("DROP TYPE paymentstatus")
    op.execute("ALTER TYPE paymentstatus_old RENAME TO paymentstatus")
