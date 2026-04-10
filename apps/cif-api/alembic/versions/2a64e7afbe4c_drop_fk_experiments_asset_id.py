"""drop_fk_experiments_asset_id

Revision ID: 2a64e7afbe4c
Revises: 3afcbd0876dd
Create Date: 2026-04-10 16:53:39.570971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a64e7afbe4c'
down_revision: Union[str, Sequence[str], None] = '3afcbd0876dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('experiments_asset_id_fkey', 'experiments', type_='foreignkey')


def downgrade() -> None:
    op.create_foreign_key(
        'experiments_asset_id_fkey', 'experiments',
        'assets', ['asset_id'], ['id']
    )
