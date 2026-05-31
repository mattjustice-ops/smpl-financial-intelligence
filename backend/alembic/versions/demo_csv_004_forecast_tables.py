"""add first-class forecast CSV tables

Revision ID: demo_csv_004
Revises: demo_csv_003
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "demo_csv_004"
down_revision: Union[str, None] = "demo_csv_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_col() -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _tenant_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE")


def _version_period_cols() -> list[sa.Column]:
    return [
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
    ]


def _money_col(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(precision=18, scale=2), nullable=True)


def _ratio_col(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(precision=18, scale=6), nullable=True)


def upgrade() -> None:
    op.create_table(
        "forecast_assumptions",
        _tenant_col(),
        sa.Column("assumption", sa.String(length=256), nullable=False),
        sa.Column("value", sa.String(length=256), nullable=True),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "assumption", name="pk_forecast_assumptions"),
    )

    op.create_table(
        "forecast_bookings_summary",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("gross_bookings_arr"),
        _money_col("weighted_pipeline_arr"),
        _ratio_col("pipeline_coverage_ratio"),
        _money_col("new_business_arr"),
        _money_col("renewal_arr"),
        _money_col("expansion_arr"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_bookings_summary"),
    )

    op.create_table(
        "forecast_cash_collections",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("beginning_cash"),
        _money_col("collections"),
        _money_col("payroll_cash_out"),
        _money_col("commission_cash_out"),
        _money_col("vendor_cash_out"),
        _money_col("marketing_cash_out"),
        _money_col("ending_cash"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_cash_collections"),
    )

    op.create_table(
        "forecast_cash_flow_statement",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("net_income"),
        _money_col("change_in_accounts_receivable"),
        _money_col("change_in_deferred_revenue"),
        _money_col("capital_expenditures"),
        _money_col("net_cash_from_operating_activities"),
        _money_col("ending_cash"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_cash_flow_statement"),
    )

    op.create_table(
        "forecast_balance_sheet",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("cash"),
        _money_col("accounts_receivable"),
        _money_col("deferred_revenue"),
        _money_col("accounts_payable"),
        _money_col("total_assets"),
        _money_col("total_liabilities"),
        _money_col("equity"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_balance_sheet"),
    )

    op.create_table(
        "forecast_income_statement",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("revenue"),
        _money_col("cost_of_revenue"),
        _money_col("gross_profit"),
        _money_col("sales_and_marketing"),
        _money_col("research_and_development"),
        _money_col("general_and_administrative"),
        _money_col("ebitda"),
        _money_col("net_income"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_income_statement"),
    )

    op.create_table(
        "forecast_headcount_plan",
        _tenant_col(),
        *_version_period_cols(),
        sa.Column("department", sa.String(length=256), nullable=False),
        sa.Column("headcount", sa.Numeric(precision=18, scale=4), nullable=True),
        _money_col("monthly_payroll_cost"),
        _money_col("total_people_cost"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", "department", name="pk_forecast_headcount_plan"),
    )

    op.create_table(
        "forecast_marketing_pipeline",
        _tenant_col(),
        *_version_period_cols(),
        sa.Column("marketing_channel", sa.String(length=256), nullable=False),
        sa.Column("mqls", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("sqls", sa.Numeric(precision=18, scale=4), nullable=True),
        _money_col("pipeline_arr_created"),
        _money_col("expected_closed_won_arr"),
        _money_col("marketing_spend"),
        _money_col("cost_per_sql"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", "marketing_channel", name="pk_forecast_marketing_pipeline"),
    )

    op.create_table(
        "forecast_mrr_waterfall",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("beginning_arr"),
        _money_col("renewal_arr"),
        _money_col("renewal_uplift_arr"),
        _money_col("new_business_arr"),
        _money_col("expansion_arr"),
        _money_col("reactivation_arr"),
        _money_col("contraction_arr"),
        _money_col("churn_arr"),
        _money_col("ending_arr"),
        _ratio_col("forecasted_nrr"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_mrr_waterfall"),
    )

    op.create_table(
        "forecast_opportunities",
        _tenant_col(),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("forecast_period", sa.Date(), nullable=False),
        sa.Column("opportunity_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=True),
        sa.Column("customer_name", sa.String(length=512), nullable=True),
        sa.Column("segment", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("marketing_channel", sa.String(length=256), nullable=True),
        sa.Column("opportunity_type", sa.String(length=128), nullable=True),
        sa.Column("stage", sa.String(length=128), nullable=True),
        _money_col("amount_arr"),
        sa.Column("probability", sa.Numeric(precision=9, scale=6), nullable=True),
        _money_col("weighted_arr"),
        sa.Column("billing_cadence", sa.String(length=64), nullable=True),
        sa.Column("billing_terms", sa.String(length=128), nullable=True),
        _ratio_col("historical_nrr_assumption"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "forecast_period", "opportunity_id", name="pk_forecast_opportunities"),
    )

    op.create_table(
        "forecast_quota_capacity",
        _tenant_col(),
        *_version_period_cols(),
        sa.Column("region", sa.String(length=128), nullable=False),
        sa.Column("quota_carrying_reps", sa.Numeric(precision=18, scale=4), nullable=True),
        _money_col("quota_capacity_arr"),
        _money_col("expected_bookings_arr"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", "region", name="pk_forecast_quota_capacity"),
    )

    op.create_table(
        "forecast_revenue_schedule",
        _tenant_col(),
        *_version_period_cols(),
        _money_col("recognized_revenue"),
        _money_col("billings"),
        _money_col("deferred_revenue_ending"),
        sa.Column("historical_dso", sa.Numeric(precision=18, scale=4), nullable=True),
        _money_col("expected_collections"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_revenue_schedule"),
    )

    op.create_table(
        "forecast_working_capital_metrics",
        _tenant_col(),
        *_version_period_cols(),
        sa.Column("dso", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("dpo", sa.Numeric(precision=18, scale=4), nullable=True),
        _money_col("accounts_receivable"),
        _money_col("deferred_revenue"),
        *_timestamps(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_working_capital_metrics"),
    )


def downgrade() -> None:
    op.drop_table("forecast_working_capital_metrics")
    op.drop_table("forecast_revenue_schedule")
    op.drop_table("forecast_quota_capacity")
    op.drop_table("forecast_opportunities")
    op.drop_table("forecast_mrr_waterfall")
    op.drop_table("forecast_marketing_pipeline")
    op.drop_table("forecast_headcount_plan")
    op.drop_table("forecast_income_statement")
    op.drop_table("forecast_balance_sheet")
    op.drop_table("forecast_cash_flow_statement")
    op.drop_table("forecast_cash_collections")
    op.drop_table("forecast_bookings_summary")
    op.drop_table("forecast_assumptions")
