"""Company profile for commentary and exports, and the demo-company flag.

Revision ID: company_profile_001
Revises: close_events_001
Create Date: 2026-11-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "company_profile_001"
down_revision: Union[str, None] = "close_events_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_profiles",
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("tagline", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("business_model", sa.Text(), nullable=True),
        sa.Column("stage", sa.String(128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("competitors", sa.JSON(), nullable=True),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("opportunities", sa.Text(), nullable=True),
        sa.Column("threats", sa.Text(), nullable=True),
        sa.Column("strategic_priorities", sa.JSON(), nullable=True),
        sa.Column("favorable_themes", sa.JSON(), nullable=True),
        sa.Column("unfavorable_themes", sa.JSON(), nullable=True),
        sa.Column("leadership_posture", sa.Text(), nullable=True),
        sa.Column("cash_floor", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("organizations", sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column("organizations", "is_demo")
    op.drop_table("organization_profiles")
