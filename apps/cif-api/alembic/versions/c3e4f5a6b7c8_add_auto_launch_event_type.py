"""add auto_launch event type (TCE-09)

Revision ID: c3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend the eventtype enum for the auto_launch signal emitted when the
    # AUTO_LAUNCH band either approves a surface for direct production
    # deployment or blocks it and routes to review.
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'auto_launch'")


def downgrade() -> None:
    # Postgres does not support dropping enum values — intentionally omitted.
    pass
