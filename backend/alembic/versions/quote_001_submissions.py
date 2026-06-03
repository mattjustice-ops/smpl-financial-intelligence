"""add quote_submissions table

Revision ID: quote_001
Revises: demo_csv_007
Create Date: 2026-05-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "quote_001"
down_revision: Union[str, None] = "demo_csv_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quote_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lead_score", sa.Integer(), nullable=False),
        sa.Column("recommended_package", sa.String(length=64), nullable=False),
        sa.Column("hubspot_contact_id", sa.String(length=64), nullable=True),
        sa.Column("hubspot_company_id", sa.String(length=64), nullable=True),
        sa.Column("hubspot_deal_id", sa.String(length=64), nullable=True),
        sa.Column("hubspot_sync_status", sa.String(length=32), nullable=False),
        sa.Column("hubspot_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_submissions_email", "quote_submissions", ["email"])


def downgrade() -> None:
    op.drop_index("ix_quote_submissions_email", table_name="quote_submissions")
    op.drop_table("quote_submissions")
