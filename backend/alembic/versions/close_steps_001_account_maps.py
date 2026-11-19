"""Company account maps, saved without a freeze pack.

Revision ID: close_steps_001
Revises: deck_palette_001
Create Date: 2026-11-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "close_steps_001"
down_revision: Union[str, None] = "deck_palette_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("gl_account_maps", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "gl_account_maps")
