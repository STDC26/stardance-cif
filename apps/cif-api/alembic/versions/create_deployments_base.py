"""create deployments base table (missing from initial schema)

Revision ID: create_deployments_base
Revises: a7290f92142f
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = 'create_deployments_base'
down_revision: Union[str, Sequence[str], None] = 'a7290f92142f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'deployments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('surface_version_id', UUID(as_uuid=True), sa.ForeignKey('surface_versions.id'), nullable=False, index=True),
        sa.Column('environment', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('deployments')
