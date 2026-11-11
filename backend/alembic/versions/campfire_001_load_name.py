"""Load name on imported rows so one named load can be removed."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "campfire_001"
down_revision: Union[str, None] = "slide_deck_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "gl_actuals",
    "customers",
    "invoices",
    "subscriptions",
    "payments",
    "opportunities",
    "headcount_plan",
    "workforce_employees",
    "workforce_open_requisitions",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("load_name", sa.String(length=256), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "load_name")
