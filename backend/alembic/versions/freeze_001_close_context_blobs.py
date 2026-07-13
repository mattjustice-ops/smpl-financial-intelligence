"""Close context freeze blobs — durable sectioned packs for Copilot / Prompt 5.

Revision ID: freeze_001
Revises: export_001
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "freeze_001"
down_revision: Union[str, None] = "export_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "close_context_blobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_period", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context_text", sa.Text(), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            name="uq_close_context_blobs_org_period",
        ),
    )
    op.create_index(
        "ix_close_context_blobs_organization_id",
        "close_context_blobs",
        ["organization_id"],
    )
    op.create_index("ix_close_context_blobs_as_of_period", "close_context_blobs", ["as_of_period"])
    op.create_index("ix_close_context_blobs_status", "close_context_blobs", ["status"])
    op.create_index(
        "ix_close_context_blobs_org_period_status",
        "close_context_blobs",
        ["organization_id", "as_of_period", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_close_context_blobs_org_period_status", table_name="close_context_blobs")
    op.drop_index("ix_close_context_blobs_status", table_name="close_context_blobs")
    op.drop_index("ix_close_context_blobs_as_of_period", table_name="close_context_blobs")
    op.drop_index("ix_close_context_blobs_organization_id", table_name="close_context_blobs")
    op.drop_table("close_context_blobs")
