"""SMPL Ops usage_events — LLM and export instrumentation

Revision ID: ops_001
Revises: forecast_001
Create Date: 2026-06-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ops_001"
down_revision: Union[str, None] = "forecast_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=12, scale=6),
            nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_organization_id", "usage_events", ["organization_id"])
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index(
        "ix_usage_events_org_created",
        "usage_events",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_org_created", table_name="usage_events")
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_event_type", table_name="usage_events")
    op.drop_index("ix_usage_events_organization_id", table_name="usage_events")
    op.drop_table("usage_events")
