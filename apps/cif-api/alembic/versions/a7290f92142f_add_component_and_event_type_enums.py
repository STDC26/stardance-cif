"""add component and event type enums

Revision ID: a7290f92142f
Revises: 0caaf841b7b2
Create Date: 2026-03-12 03:41:05.801264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7290f92142f'
down_revision: Union[str, Sequence[str], None] = '0caaf841b7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types
    componenttype = sa.Enum(
        'hero', 'text_block', 'image', 'video', 'cta', 'form',
        'offer_stack', 'social_proof', 'testimonial', 'faq',
        'diagnostic_entry', 'trust_bar',
        name='componenttype'
    )
    componenttype.create(op.get_bind(), checkfirst=True)

    eventtype = sa.Enum(
        'surface_view', 'surface_engaged', 'component_impression',
        'component_click', 'form_start', 'form_submit',
        'diagnostic_start', 'diagnostic_complete', 'offer_view', 'conversion',
        name='eventtype'
    )
    eventtype.create(op.get_bind(), checkfirst=True)

    # components: rename type -> component_type and change to enum
    op.add_column('components', sa.Column('component_type', componenttype, nullable=True))
    op.execute("UPDATE components SET component_type = type::componenttype")
    op.alter_column('components', 'component_type', nullable=False)
    op.drop_column('components', 'type')

    # signal_events: add session_id, convert event_type to enum
    op.add_column('signal_events', sa.Column('session_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_signal_events_session_id'), 'signal_events', ['session_id'], unique=False)
    op.execute("ALTER TABLE signal_events ALTER COLUMN event_type TYPE eventtype USING event_type::eventtype")

    # surface_components: add section_id with default
    op.add_column('surface_components', sa.Column('section_id', sa.String(length=100), nullable=False, server_default='main'))
    op.alter_column('surface_components', 'section_id', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # surface_components: drop section_id
    op.drop_column('surface_components', 'section_id')

    # signal_events: revert event_type to varchar, drop session_id
    op.execute("ALTER TABLE signal_events ALTER COLUMN event_type TYPE varchar(100) USING event_type::text")
    op.drop_index(op.f('ix_signal_events_session_id'), table_name='signal_events')
    op.drop_column('signal_events', 'session_id')

    # components: revert component_type enum to type varchar
    op.add_column('components', sa.Column('type', sa.VARCHAR(length=100), nullable=True))
    op.execute("UPDATE components SET type = component_type::text")
    op.alter_column('components', 'type', nullable=False)
    op.drop_column('components', 'component_type')

    # Drop enum types
    sa.Enum(name='eventtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='componenttype').drop(op.get_bind(), checkfirst=True)
