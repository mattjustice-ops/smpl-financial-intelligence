"""Company board-deck colors on the organization.

Revision ID: deck_palette_001
Revises: campfire_001
Create Date: 2026-11-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "deck_palette_001"
down_revision: Union[str, None] = "campfire_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("deck_palette", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "deck_palette")
