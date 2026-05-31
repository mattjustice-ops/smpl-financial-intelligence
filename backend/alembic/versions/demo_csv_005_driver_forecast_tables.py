"""add driver based forecast schedules

Revision ID: demo_csv_005
Revises: demo_csv_004
Create Date: 2026-05-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "demo_csv_005"
down_revision: Union[str, None] = "demo_csv_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_col() -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _money(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(precision=18, scale=2), nullable=True)


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())

    if "forecast_driver_assumptions" not in existing:
        op.create_table(
        "forecast_driver_assumptions",
        _tenant_col(),
        sa.Column("assumption_name", sa.String(length=256), nullable=False),
        sa.Column("assumption_category", sa.String(length=128), nullable=True),
        sa.Column("actual_value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("forecast_value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("effective_period", sa.Date(), nullable=False),
        sa.Column("scenario_name", sa.String(length=128), nullable=False, server_default="Forecast"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "effective_period",
            "assumption_name",
            name="pk_forecast_driver_assumptions",
        ),
        )

    if "forecast_deferred_revenue_waterfall" not in existing:
        op.create_table(
        "forecast_deferred_revenue_waterfall",
        _tenant_col(),
        sa.Column("scenario_name", sa.String(length=128), nullable=False, server_default="Forecast"),
        sa.Column("period", sa.Date(), nullable=False),
        _money("beginning_deferred_revenue"),
        _money("new_billings"),
        _money("revenue_recognized"),
        _money("ending_deferred_revenue"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "period",
            name="pk_forecast_deferred_revenue_waterfall",
        ),
        )

    if "forecast_operating_cash_flow_bridge" not in existing:
        op.create_table(
        "forecast_operating_cash_flow_bridge",
        _tenant_col(),
        sa.Column("scenario_name", sa.String(length=128), nullable=False, server_default="Forecast"),
        sa.Column("period", sa.Date(), nullable=False),
        _money("net_income"),
        _money("depreciation_and_amortization"),
        _money("stock_based_compensation"),
        _money("noncash_items"),
        _money("change_in_accounts_receivable"),
        _money("change_in_deferred_revenue"),
        _money("change_in_accounts_payable"),
        _money("change_in_prepaids"),
        _money("change_in_other_working_capital"),
        _money("net_cash_from_operating_activities"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "period",
            name="pk_forecast_operating_cash_flow_bridge",
        ),
        )


def downgrade() -> None:
    op.drop_table("forecast_operating_cash_flow_bridge")
    op.drop_table("forecast_deferred_revenue_waterfall")
    op.drop_table("forecast_driver_assumptions")
