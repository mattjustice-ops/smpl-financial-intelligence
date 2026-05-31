"""add rep_id column to opportunities

Revision ID: demo_csv_002
Revises: demo_csv_001
Create Date: 2026-05-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "demo_csv_002"
down_revision: Union[str, None] = "demo_csv_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("rep_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "rep_id")
