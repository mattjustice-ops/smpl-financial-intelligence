"""Plan assessments table for version-keyed Plan Assurance persistence.

Revision ID: ppi_001
Revises: budget_001
Create Date: 2026-09-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ppi_001"
down_revision: Union[str, None] = "budget_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forecast_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scenario", sa.String(length=64), nullable=False, server_default="budget"),
        sa.Column("period_label", sa.String(length=128), nullable=True),
        sa.Column("budget_year", sa.Integer(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feasibility_verdict", sa.String(length=32), nullable=False),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("simulation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("method_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prior_source", sa.String(length=64), nullable=True),
        sa.Column("mc_seed", sa.Integer(), nullable=True),
        sa.Column("citation_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["budget_version_id"], ["budget_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["forecast_version_id"], ["forecast_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_assessments_organization_id", "plan_assessments", ["organization_id"])
    op.create_index(
        "ix_plan_assessments_budget_version_id", "plan_assessments", ["budget_version_id"]
    )
    op.create_index(
        "ix_plan_assessments_forecast_version_id",
        "plan_assessments",
        ["forecast_version_id"],
    )
    op.create_index(
        "ix_plan_assessments_org_budget_asof",
        "plan_assessments",
        ["organization_id", "budget_version_id", "as_of"],
    )


def downgrade() -> None:
    op.drop_index("ix_plan_assessments_org_budget_asof", table_name="plan_assessments")
    op.drop_index("ix_plan_assessments_forecast_version_id", table_name="plan_assessments")
    op.drop_index("ix_plan_assessments_budget_version_id", table_name="plan_assessments")
    op.drop_index("ix_plan_assessments_organization_id", table_name="plan_assessments")
    op.drop_table("plan_assessments")
