"""Company slide-deck templates for the close.

Revision ID: slide_deck_001
Revises: budget_002
Create Date: 2026-11-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "slide_deck_001"
down_revision: Union[str, None] = "budget_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slide_deck_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("slide_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_slide_deck_templates_organization_id",
        "slide_deck_templates",
        ["organization_id"],
    )
    op.create_index(
        "ix_slide_deck_templates_status",
        "slide_deck_templates",
        ["status"],
    )
    op.create_index(
        "uq_slide_deck_templates_one_active",
        "slide_deck_templates",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_slide_deck_templates_one_active", table_name="slide_deck_templates")
    op.drop_index("ix_slide_deck_templates_status", table_name="slide_deck_templates")
    op.drop_index("ix_slide_deck_templates_organization_id", table_name="slide_deck_templates")
    op.drop_table("slide_deck_templates")
