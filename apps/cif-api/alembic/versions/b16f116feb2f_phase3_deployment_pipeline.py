"""phase3 deployment pipeline

Revision ID: b16f116feb2f
Revises: a7290f92142f
Create Date: 2026-03-12 10:15:30.595556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b16f116feb2f'
down_revision: Union[str, Sequence[str], None] = 'create_deployments_base'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # --- surfaces: add slug column ---
    # Add as nullable first, backfill, then make NOT NULL
    op.add_column('surfaces', sa.Column('slug', sa.String(length=255), nullable=True))

    # Backfill slugs for existing surfaces using lower(name) with id suffix for uniqueness
    op.execute("""
        UPDATE surfaces
        SET slug = lower(regexp_replace(regexp_replace(name, '[^\\w\\s-]', '', 'g'), '[\\s_]+', '-', 'g'))
                   || '-' || left(id::text, 4)
        WHERE slug IS NULL
    """)

    op.alter_column('surfaces', 'slug', nullable=False)
    op.create_index(op.f('ix_surfaces_slug'), 'surfaces', ['slug'], unique=True)

    # --- surface_versions: add review pipeline columns ---
    # Create enum type first
    reviewstate_enum = sa.Enum('draft', 'review', 'published', 'archived', name='reviewstate')
    reviewstate_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('surface_versions', sa.Column(
        'review_state', reviewstate_enum, nullable=True
    ))
    op.add_column('surface_versions', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('surface_versions', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill existing versions as draft
    op.execute("UPDATE surface_versions SET review_state = 'draft' WHERE review_state IS NULL")
    op.alter_column('surface_versions', 'review_state', nullable=False)

    # --- deployments: add new columns and convert types ---
    # Create enum types
    env_enum = sa.Enum('preview', 'staging', 'production', name='deploymentenvironment')
    env_enum.create(op.get_bind(), checkfirst=True)
    status_enum = sa.Enum('pending', 'active', 'inactive', 'failed', name='deploymentstatus')
    status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('deployments', sa.Column('surface_id', sa.UUID(), nullable=True))
    op.add_column('deployments', sa.Column('deployed_by', sa.String(length=255), nullable=True))
    op.add_column('deployments', sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('deployments', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # Backfill surface_id from surface_versions for any existing rows
    op.execute("""
        UPDATE deployments d
        SET surface_id = sv.surface_id
        FROM surface_versions sv
        WHERE d.surface_version_id = sv.id
          AND d.surface_id IS NULL
    """)

    # Convert environment and status columns to enum types
    op.execute("ALTER TABLE deployments ALTER COLUMN environment TYPE deploymentenvironment USING environment::deploymentenvironment")
    op.execute("ALTER TABLE deployments ALTER COLUMN status TYPE deploymentstatus USING status::deploymentstatus")

    # Now make surface_id NOT NULL (after backfill)
    op.alter_column('deployments', 'surface_id', nullable=False)

    op.create_index(op.f('ix_deployments_surface_id'), 'deployments', ['surface_id'], unique=False)
    op.create_foreign_key('deployments_surface_id_fkey', 'deployments', 'surfaces', ['surface_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('deployments_surface_id_fkey', 'deployments', type_='foreignkey')
    op.drop_index(op.f('ix_deployments_surface_id'), table_name='deployments')

    op.execute("ALTER TABLE deployments ALTER COLUMN status TYPE varchar(50) USING status::text")
    op.execute("ALTER TABLE deployments ALTER COLUMN environment TYPE varchar(100) USING environment::text")

    op.drop_column('deployments', 'created_at')
    op.drop_column('deployments', 'deactivated_at')
    op.drop_column('deployments', 'deployed_by')
    op.drop_column('deployments', 'surface_id')

    op.drop_column('surface_versions', 'published_at')
    op.drop_column('surface_versions', 'reviewed_at')
    op.drop_column('surface_versions', 'review_state')

    op.drop_index(op.f('ix_surfaces_slug'), table_name='surfaces')
    op.drop_column('surfaces', 'slug')

    sa.Enum(name='reviewstate').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='deploymentenvironment').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='deploymentstatus').drop(op.get_bind(), checkfirst=True)
