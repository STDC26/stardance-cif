"""initial schema

Revision ID: 0caaf841b7b2
Revises: 
Create Date: 2026-03-12 01:07:51.434937

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '0caaf841b7b2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('surfaces',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('funnel_stage', sa.String(100), nullable=True),
        sa.Column('surface_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('surface_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('surface_id', UUID(as_uuid=True), sa.ForeignKey('surfaces.id'), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('components',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('surface_components',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('surface_version_id', UUID(as_uuid=True), sa.ForeignKey('surface_versions.id'), nullable=False, index=True),
        sa.Column('component_id', UUID(as_uuid=True), sa.ForeignKey('components.id'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('signal_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('surface_id', UUID(as_uuid=True), sa.ForeignKey('surfaces.id'), nullable=True, index=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('signal_events')
    op.drop_table('surface_components')
    op.drop_table('components')
    op.drop_table('surface_versions')
    op.drop_table('surfaces')
