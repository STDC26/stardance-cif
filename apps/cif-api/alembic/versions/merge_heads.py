"""merge two alembic heads: enum fix + phase5 intelligence

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6, phase5_intelligence_schema
Create Date: 2026-04-11 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'phase5_intelligence_schema')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
