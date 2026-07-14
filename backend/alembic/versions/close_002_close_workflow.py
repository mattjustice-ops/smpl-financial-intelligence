"""Customer Close Workflow — lock events, load receipts, session workflow columns.

Revision ID: close_002
Revises: close_001
Create Date: 2026-07-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "close_002"
down_revision: Union[str, None] = "close_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "close_sessions",
        sa.Column("workflow_state", sa.String(length=64), nullable=False, server_default="OPEN"),
    )
    op.add_column(
        "close_sessions",
        sa.Column("current_lock_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "close_sessions",
        sa.Column("certified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_close_sessions_workflow_state", "close_sessions", ["workflow_state"])

    op.create_table(
        "close_lock_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("close_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_period", sa.String(length=7), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("checklist_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("locked_by", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["close_session_id"], ["close_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "close_session_id",
            "lock_version",
            "event_type",
            name="uq_close_lock_events_session_version_type",
        ),
    )
    op.create_index("ix_close_lock_events_organization_id", "close_lock_events", ["organization_id"])
    op.create_index("ix_close_lock_events_close_session_id", "close_lock_events", ["close_session_id"])
    op.create_index("ix_close_lock_events_as_of_period", "close_lock_events", ["as_of_period"])

    op.create_table(
        "close_load_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("close_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingest_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("as_of_period", sa.String(length=7), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rows_staged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_applied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["close_session_id"], ["close_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ingest_batch_id"], ["ingest_batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_close_load_receipts_organization_id",
        "close_load_receipts",
        ["organization_id"],
    )
    op.create_index(
        "ix_close_load_receipts_as_of_period",
        "close_load_receipts",
        ["as_of_period"],
    )
    op.create_index(
        "ix_close_load_receipts_close_session_id",
        "close_load_receipts",
        ["close_session_id"],
    )
    op.create_index(
        "ix_close_load_receipts_ingest_batch_id",
        "close_load_receipts",
        ["ingest_batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_close_load_receipts_ingest_batch_id", table_name="close_load_receipts")
    op.drop_index("ix_close_load_receipts_close_session_id", table_name="close_load_receipts")
    op.drop_index("ix_close_load_receipts_as_of_period", table_name="close_load_receipts")
    op.drop_index("ix_close_load_receipts_organization_id", table_name="close_load_receipts")
    op.drop_table("close_load_receipts")

    op.drop_index("ix_close_lock_events_as_of_period", table_name="close_lock_events")
    op.drop_index("ix_close_lock_events_close_session_id", table_name="close_lock_events")
    op.drop_index("ix_close_lock_events_organization_id", table_name="close_lock_events")
    op.drop_table("close_lock_events")

    op.drop_index("ix_close_sessions_workflow_state", table_name="close_sessions")
    op.drop_column("close_sessions", "certified_at")
    op.drop_column("close_sessions", "current_lock_version")
    op.drop_column("close_sessions", "workflow_state")
