"""add qualified and warm to qds_qualification_status_enum

Revision ID: a1b2c3d4e5f6
Revises: 2a64e7afbe4c
Create Date: 2026-04-11 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2a64e7afbe4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE qds_qualification_status_enum ADD VALUE IF NOT EXISTS 'qualified'")
    op.execute("ALTER TYPE qds_qualification_status_enum ADD VALUE IF NOT EXISTS 'warm'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
