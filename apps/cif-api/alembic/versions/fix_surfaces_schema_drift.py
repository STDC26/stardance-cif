"""fix surfaces schema drift — surface_type->type, add description, version->version_number

Revision ID: fix_surfaces_schema_drift
Revises: phase5_intelligence_schema
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'fix_surfaces_schema_drift'
down_revision: Union[str, Sequence[str], None] = 'phase5_intelligence_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # surfaces: rename surface_type -> type
    op.alter_column('surfaces', 'surface_type', new_column_name='type')

    # surfaces: add description column
    op.add_column('surfaces', sa.Column('description', sa.String(1000), nullable=True))

    # surface_versions: rename version -> version_number
    op.alter_column('surface_versions', 'version', new_column_name='version_number')


def downgrade() -> None:
    op.alter_column('surface_versions', 'version_number', new_column_name='version')
    op.drop_column('surfaces', 'description')
    op.alter_column('surfaces', 'type', new_column_name='surface_type')
