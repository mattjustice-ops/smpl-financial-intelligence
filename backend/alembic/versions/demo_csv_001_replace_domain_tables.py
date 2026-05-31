"""replace legacy domain tables with demo CSV-aligned schema

Revision ID: demo_csv_001
Revises: e468aa4669fc
Create Date: 2026-05-12

"""

from __future__ import annotations

from importlib import util
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "demo_csv_001"
down_revision: Union[str, None] = "e468aa4669fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _e468_mod():
    path = Path(__file__).resolve().parent / "e468aa4669fc_add_financial_domain_tables.py"
    spec = util.spec_from_file_location("_e468_financial_domain_module", path)
    assert spec and spec.loader
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def upgrade() -> None:
    _e468_mod().downgrade()

    op.create_table(
        "customers",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("customer_name", sa.String(length=512), nullable=False),
        sa.Column("segment", sa.String(length=128), nullable=True),
        sa.Column("industry", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("billing_cadence", sa.String(length=64), nullable=True),
        sa.Column("payment_terms", sa.String(length=128), nullable=True),
        sa.Column("source_crm", sa.String(length=128), nullable=True),
        sa.Column("netsuite_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "customer_id", name="pk_customers"),
    )
    op.create_table(
        "subscriptions",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("product", sa.String(length=512), nullable=True),
        sa.Column("billing_cadence", sa.String(length=64), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("current_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("current_arr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_subscriptions_customer",
        ),
        sa.PrimaryKeyConstraint("organization_id", "subscription_id", name="pk_subscriptions"),
    )
    op.create_table(
        "opportunities",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("opportunity_name", sa.String(length=512), nullable=False),
        sa.Column("opportunity_type", sa.String(length=128), nullable=True),
        sa.Column("stage", sa.String(length=128), nullable=True),
        sa.Column("amount_arr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("probability", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("segment", sa.String(length=128), nullable=True),
        sa.Column("owner", sa.String(length=512), nullable=True),
        sa.Column("forecast_period", sa.String(length=64), nullable=True),
        sa.Column("source_crm", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_opportunities_customer",
        ),
        sa.PrimaryKeyConstraint("organization_id", "opportunity_id", name="pk_opportunities"),
    )
    op.create_table(
        "invoices",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("invoice_period", sa.String(length=64), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("invoice_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("payment_status", sa.String(length=64), nullable=True),
        sa.Column("billing_cadence", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_invoices_customer",
        ),
        sa.PrimaryKeyConstraint("organization_id", "invoice_id", name="pk_invoices"),
    )
    op.create_table(
        "payments",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", sa.String(length=128), nullable=False),
        sa.Column("invoice_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("payment_method", sa.String(length=128), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "invoice_id"],
            ["invoices.organization_id", "invoices.invoice_id"],
            ondelete="RESTRICT",
            name="fk_payments_invoice",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_payments_customer",
        ),
        sa.PrimaryKeyConstraint("organization_id", "payment_id", name="pk_payments"),
    )
    op.create_table(
        "gl_actuals",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=False),
        sa.Column("account_name", sa.String(length=512), nullable=True),
        sa.Column("statement", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("subsidiary", sa.String(length=128), server_default="", nullable=False),
        sa.Column("source_system", sa.String(length=64), server_default="demo", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "period",
            "account_number",
            "subsidiary",
            "source_system",
            name="pk_gl_actuals",
        ),
    )
    op.create_table(
        "headcount_plan",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("department", sa.String(length=256), nullable=False),
        sa.Column("headcount", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("monthly_payroll_cost", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "period", "department", name="pk_headcount_plan"),
    )
    op.create_table(
        "vendor_contracts",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", sa.String(length=128), nullable=False),
        sa.Column("vendor_name", sa.String(length=512), nullable=True),
        sa.Column("service_category", sa.String(length=256), nullable=True),
        sa.Column("contract_start", sa.Date(), nullable=True),
        sa.Column("contract_end", sa.Date(), nullable=True),
        sa.Column("annual_contract_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("billing_cadence", sa.String(length=64), nullable=True),
        sa.Column("payment_terms", sa.String(length=128), nullable=True),
        sa.Column("expense_category", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "vendor_id", name="pk_vendor_contracts"),
    )
    op.create_table(
        "sales_quotas",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rep_id", sa.String(length=128), nullable=False),
        sa.Column("rep_name", sa.String(length=512), nullable=True),
        sa.Column("segment", sa.String(length=128), server_default="", nullable=False),
        sa.Column("quota_period", sa.String(length=64), nullable=False),
        sa.Column("quota_arr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("closed_won_arr_to_date", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "organization_id", "rep_id", "quota_period", "segment", name="pk_sales_quotas"
        ),
    )
    op.create_table(
        "commission_plans",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=True),
        sa.Column("eligible_opportunity_type", sa.String(length=256), nullable=True),
        sa.Column("base_commission_rate", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("accelerator_multiplier", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("accelerator_threshold", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("accelerated_rate", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("clawback_window", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "plan_id", name="pk_commission_plans_demo"),
    )
    op.create_table(
        "mrr_waterfall",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("beginning_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("new_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("expansion_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("contraction_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("churn_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("reactivation_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("ending_mrr", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("movement_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_mrr_waterfall_customer",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "period", "customer_id", "movement_type", name="pk_mrr_waterfall"
        ),
    )


def downgrade() -> None:
    op.drop_table("mrr_waterfall")
    op.drop_table("commission_plans")
    op.drop_table("sales_quotas")
    op.drop_table("vendor_contracts")
    op.drop_table("headcount_plan")
    op.drop_table("gl_actuals")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("opportunities")
    op.drop_table("subscriptions")
    op.drop_table("customers")
    _e468_mod().upgrade()
