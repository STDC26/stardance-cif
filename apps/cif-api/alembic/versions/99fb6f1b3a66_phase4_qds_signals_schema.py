"""phase4 qds signals schema

Revision ID: 99fb6f1b3a66
Revises: 4f767890ce95
Create Date: 2026-03-12 15:17:56.181419

Changes:
  - Add 4 new QDS event types to the eventtype PG enum
  - Make signal_events.surface_id nullable (QDS signals have no surface)
  - Drop FK constraint on surface_id so QDS asset UUIDs can be stored
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99fb6f1b3a66'
down_revision: Union[str, Sequence[str], None] = '4f767890ce95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add new QDS event types to the PG enum
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'step_view'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'answer_submitted'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'branch_selected'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'qualification_result'")

    # 2. Drop FK constraint on surface_id so QDS asset UUIDs can be stored
    op.drop_constraint('signal_events_surface_id_fkey', 'signal_events', type_='foreignkey')

    # 3. Make surface_id nullable
    op.alter_column('signal_events', 'surface_id', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('signal_events', 'surface_id', nullable=False)
    op.create_foreign_key(
        'signal_events_surface_id_fkey', 'signal_events',
        'surfaces', ['surface_id'], ['id']
    )
    # Note: Cannot remove enum values in PostgreSQL
