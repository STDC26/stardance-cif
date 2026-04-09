"""add_event_data_to_signal_events

Revision ID: 3afcbd0876dd
Revises: fix_surfaces_schema_drift
Create Date: 2026-04-09 16:24:28.973136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3afcbd0876dd'
down_revision: Union[str, Sequence[str], None] = 'fix_surfaces_schema_drift'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('signal_events',
        sa.Column('event_data', postgresql.JSONB(), nullable=True)
    )
    op.drop_column('signal_events', 'payload')


def downgrade() -> None:
    op.add_column('signal_events',
        sa.Column('payload', sa.Text(), nullable=True)
    )
    op.drop_column('signal_events', 'event_data')
