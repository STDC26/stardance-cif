"""add a2_pipeline_complete event type (TCE-11 Path 3)

Revision ID: c4f5a6b7c8d9
Revises: c3e4f5a6b7c8
Create Date: 2026-04-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "c3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'a2_pipeline_complete'"
    )


def downgrade() -> None:
    # Postgres does not support dropping enum values — intentionally omitted.
    pass
