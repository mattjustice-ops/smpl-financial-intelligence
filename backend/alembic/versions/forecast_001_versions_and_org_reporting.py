"""Forecast version registry + org reporting settings

Revision ID: forecast_001
Revises: auth_002
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "forecast_001"
down_revision: Union[str, None] = "auth_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("close_month", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "fiscal_year_end_month",
            sa.Integer(),
            nullable=False,
            server_default="12",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "active_forecast_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_table(
        "forecast_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("horizon", sa.String(length=32), nullable=True),
        sa.Column("as_of_period", sa.String(length=7), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("levers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("req_active", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("table_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_forecast_versions_org_status",
        "forecast_versions",
        ["organization_id", "status"],
    )
    op.create_foreign_key(
        "fk_organizations_active_forecast_version",
        "organizations",
        "forecast_versions",
        ["active_forecast_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_organizations_active_forecast_version", "organizations", type_="foreignkey")
    op.drop_index("ix_forecast_versions_org_status", table_name="forecast_versions")
    op.drop_table("forecast_versions")
    op.drop_column("organizations", "active_forecast_version_id")
    op.drop_column("organizations", "fiscal_year_end_month")
    op.drop_column("organizations", "close_month")
