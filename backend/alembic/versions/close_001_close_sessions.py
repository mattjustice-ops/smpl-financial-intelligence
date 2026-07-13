"""Close sessions — immutable (org, period) lineage anchors (Close Peak §4E).

Revision ID: close_001
Revises: freeze_001
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "close_001"
down_revision: Union[str, None] = "freeze_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "close_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_period", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "as_of_period",
            name="uq_close_sessions_org_period",
        ),
    )
    op.create_index("ix_close_sessions_organization_id", "close_sessions", ["organization_id"])
    op.create_index("ix_close_sessions_as_of_period", "close_sessions", ["as_of_period"])
    op.create_index("ix_close_sessions_status", "close_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_close_sessions_status", table_name="close_sessions")
    op.drop_index("ix_close_sessions_as_of_period", table_name="close_sessions")
    op.drop_index("ix_close_sessions_organization_id", table_name="close_sessions")
    op.drop_table("close_sessions")
