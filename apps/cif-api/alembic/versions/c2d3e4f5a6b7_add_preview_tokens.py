"""add preview_tokens table + asset_reviewed eventtype (TCE-10)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "preview_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("preview_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_slug", sa.String(length=255), nullable=False),
        sa.Column("version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "review_state",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_preview_tokens_preview_id",
        "preview_tokens",
        ["preview_id"],
        unique=True,
    )
    op.create_index(
        "idx_preview_tokens_asset_id",
        "preview_tokens",
        ["asset_id"],
    )

    # Extend the eventtype enum for the asset_reviewed signal emitted on
    # preview approve/reject. Pattern copied from phase4_qds_signals_schema.
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'asset_reviewed'")


def downgrade() -> None:
    op.drop_index("idx_preview_tokens_asset_id", table_name="preview_tokens")
    op.drop_index("idx_preview_tokens_preview_id", table_name="preview_tokens")
    op.drop_table("preview_tokens")
    # Postgres does not support dropping enum values — intentionally omitted.
