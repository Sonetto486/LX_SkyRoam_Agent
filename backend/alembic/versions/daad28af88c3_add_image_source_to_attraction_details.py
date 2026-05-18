"""add_image_source_to_attraction_details

Revision ID: daad28af88c3
Revises: 4712b94ac0d8
Create Date: 2026-05-18 18:10:50.457893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daad28af88c3'
down_revision: Union[str, None] = '4712b94ac0d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attraction_details', sa.Column('image_source', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('attraction_details', 'image_source')
