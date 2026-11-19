"""Company words for a contract event.

Revision ID: close_events_001
Revises: close_steps_001
Create Date: 2026-11-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "close_events_001"
down_revision: Union[str, None] = "close_steps_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("contract_event_labels", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "contract_event_labels")
