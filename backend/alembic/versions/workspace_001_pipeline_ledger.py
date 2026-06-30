"""Customer workspace — ingest batches + pipeline events (CSV + API)

Revision ID: workspace_001
Revises: ops_001
Create Date: 2026-06-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "workspace_001"
down_revision: Union[str, None] = "ops_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingest_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("external_batch_id", sa.String(length=256), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column("period", sa.String(length=7), nullable=True),
        sa.Column("rows_staged", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_imported", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_ingest_batches_org_idempotency",
        ),
    )
    op.create_index("ix_ingest_batches_organization_id", "ingest_batches", ["organization_id"])
    op.create_index("ix_ingest_batches_status", "ingest_batches", ["status"])
    op.create_index("ix_ingest_batches_created_at", "ingest_batches", ["created_at"])
    op.create_index(
        "ix_ingest_batches_org_created",
        "ingest_batches",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "pipeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=True),
        sa.Column("period", sa.String(length=7), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(length=256), nullable=True),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
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
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["ingest_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_events_organization_id", "pipeline_events", ["organization_id"])
    op.create_index("ix_pipeline_events_batch_id", "pipeline_events", ["batch_id"])
    op.create_index("ix_pipeline_events_event_type", "pipeline_events", ["event_type"])
    op.create_index("ix_pipeline_events_created_at", "pipeline_events", ["created_at"])
    op.create_index(
        "ix_pipeline_events_org_created",
        "pipeline_events",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_events_org_created", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_created_at", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_event_type", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_batch_id", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_organization_id", table_name="pipeline_events")
    op.drop_table("pipeline_events")

    op.drop_index("ix_ingest_batches_org_created", table_name="ingest_batches")
    op.drop_index("ix_ingest_batches_created_at", table_name="ingest_batches")
    op.drop_index("ix_ingest_batches_status", table_name="ingest_batches")
    op.drop_index("ix_ingest_batches_organization_id", table_name="ingest_batches")
    op.drop_table("ingest_batches")
