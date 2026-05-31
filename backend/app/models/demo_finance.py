"""
Demo finance tables: column names align with demo CSV headers.
Composite primary keys use (organization_id, <business_id>) where applicable.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationRefMixin:
    """organization_id is part of composite PK on all demo tables."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )


class TimestampMixinDemo:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Customer(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "customers"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "customer_id", name="pk_customers"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(512), nullable=False)
    segment: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    billing_cadence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_crm: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    netsuite_customer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    organization = relationship("Organization", back_populates="demo_customers")


class Subscription(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "subscription_id", name="pk_subscriptions"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_subscriptions_customer",
        ),
    )

    subscription_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    billing_cadence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    current_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    current_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    organization = relationship("Organization", back_populates="demo_subscriptions")


class Opportunity(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "opportunity_id", name="pk_opportunities"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_opportunities_customer",
        ),
    )

    opportunity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    opportunity_name: Mapped[str] = mapped_column(String(512), nullable=False)
    opportunity_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    amount_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expected_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    probability: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    segment: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    rep_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    forecast_period: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_crm: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    organization = relationship("Organization", back_populates="demo_opportunities")


class Invoice(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "invoice_id", name="pk_invoices"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_invoices_customer",
        ),
    )

    invoice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_period: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payment_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    billing_cadence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    organization = relationship("Organization", back_populates="demo_invoices")


class Payment(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "payments"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "payment_id", name="pk_payments"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "invoice_id"],
            ["invoices.organization_id", "invoices.invoice_id"],
            ondelete="RESTRICT",
            name="fk_payments_invoice",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_payments_customer",
        ),
    )

    payment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    organization = relationship("Organization", back_populates="demo_payments")


class GlActual(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "gl_actuals"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "version",
            "period",
            "account_number",
            "department",
            "cost_center",
            "sub_department",
            "source_file",
            "source_record_id",
            "subsidiary",
            "source_system",
            name="pk_gl_actuals",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    period: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Actual")
    account_number: Mapped[str] = mapped_column(String(64), nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    statement: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    statement_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    account_group: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expense_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    department: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    cost_center: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    sub_department: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    vendor_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vendor_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_file: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    source_record_id: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    subsidiary: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source_system: Mapped[str] = mapped_column(String(64), nullable=False, default="demo")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization = relationship("Organization", back_populates="demo_gl_actuals")


class ForecastGlDetail(OrganizationRefMixin, TimestampMixinDemo, Base):
    """Forecast-month GL detail (Forecast_gl_detail.csv) — synced to gl_actuals for drilldown."""

    __tablename__ = "forecast_gl_detail"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "scenario",
            "period",
            "gl_account",
            "department",
            "account_group",
            "expense_type",
            "sub_department",
            name="pk_forecast_gl_detail",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    scenario: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    period: Mapped[date] = mapped_column(Date, nullable=False)
    line_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    statement_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    department: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    sub_department: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    account_group: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expense_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gl_account: Mapped[str] = mapped_column(String(256), nullable=False)
    management_view_include: Mapped[str] = mapped_column(String(8), nullable=False, default="Yes")
    accounting_view_include: Mapped[str] = mapped_column(String(8), nullable=False, default="Yes")
    sbc_flag: Mapped[str] = mapped_column(String(8), nullable=False, default="No")
    one_time_flag: Mapped[str] = mapped_column(String(8), nullable=False, default="No")
    non_cash_flag: Mapped[str] = mapped_column(String(8), nullable=False, default="No")
    forecast_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization = relationship("Organization", back_populates="demo_forecast_gl_detail")


class WarehouseCsvRow(OrganizationRefMixin, TimestampMixinDemo, Base):
    """Raw landing table for expanded analysis CSVs that are not canonical marts."""

    __tablename__ = "warehouse_csv_rows"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "csv_kind",
            "source_row_number",
            name="pk_warehouse_csv_rows",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    csv_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    source_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    organization = relationship("Organization", back_populates="demo_warehouse_csv_rows")


class HeadcountPlan(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "headcount_plan"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", "department", name="pk_headcount_plan"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Actual")
    period: Mapped[date] = mapped_column(Date, nullable=False)
    department: Mapped[str] = mapped_column(String(256), nullable=False)
    headcount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    monthly_payroll_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payroll_tax_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    benefits_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    total_people_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    organization = relationship("Organization", back_populates="demo_headcount_plan")


class VendorContract(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "vendor_contracts"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "vendor_id", name="pk_vendor_contracts"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    vendor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    service_category: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    contract_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    annual_contract_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    billing_cadence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expense_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    organization = relationship("Organization", back_populates="demo_vendor_contracts")


class SalesQuota(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "sales_quotas"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id", "rep_id", "quota_period", "segment", name="pk_sales_quotas"
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    rep_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rep_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    segment: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    quota_period: Mapped[str] = mapped_column(String(64), nullable=False)
    quota_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    closed_won_arr_to_date: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    organization = relationship("Organization", back_populates="demo_sales_quotas")


class DemoCommissionPlan(OrganizationRefMixin, TimestampMixinDemo, Base):
    """Demo commission_plans CSV (distinct from legacy domain commission_plans)."""

    __tablename__ = "commission_plans"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "plan_id", name="pk_commission_plans_demo"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    eligible_opportunity_type: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    base_commission_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    accelerator_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    accelerator_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    accelerated_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    clawback_window: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    organization = relationship("Organization", back_populates="demo_commission_plans")


class ForecastAssumption(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_assumptions"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "assumption", name="pk_forecast_assumptions"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    assumption: Mapped[str] = mapped_column(String(256), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class ForecastBookingsSummary(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_bookings_summary"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_bookings_summary"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    gross_bookings_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    weighted_pipeline_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    pipeline_coverage_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    new_business_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    renewal_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expansion_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastCashCollections(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_cash_collections"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_cash_collections"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    beginning_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    collections: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    payroll_cash_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    commission_cash_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    vendor_cash_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    marketing_cash_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ending_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastCashFlowStatement(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_cash_flow_statement"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_cash_flow_statement"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_accounts_receivable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    capital_expenditures: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    net_cash_from_operating_activities: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ending_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastBalanceSheet(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_balance_sheet"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_balance_sheet"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    accounts_receivable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    accounts_payable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    total_liabilities: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastIncomeStatement(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_income_statement"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_income_statement"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    cost_of_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    gross_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    sales_and_marketing: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    research_and_development: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    general_and_administrative: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ebitda: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastHeadcountPlan(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_headcount_plan"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", "department", name="pk_forecast_headcount_plan"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    department: Mapped[str] = mapped_column(String(256), nullable=False)
    headcount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    monthly_payroll_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    total_people_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastMarketingPipeline(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_marketing_pipeline"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", "marketing_channel", name="pk_forecast_marketing_pipeline"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    marketing_channel: Mapped[str] = mapped_column(String(256), nullable=False)
    mqls: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    sqls: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    pipeline_arr_created: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expected_closed_won_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    marketing_spend: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    cost_per_sql: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastMrrWaterfall(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_mrr_waterfall"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_mrr_waterfall"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    beginning_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    renewal_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    renewal_uplift_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    new_business_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expansion_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    reactivation_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    contraction_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    churn_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ending_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    forecasted_nrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)


class ForecastOpportunity(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_opportunities"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "forecast_period", "opportunity_id", name="pk_forecast_opportunities"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    forecast_period: Mapped[date] = mapped_column(Date, nullable=False)
    opportunity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    segment: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    marketing_channel: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    opportunity_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    amount_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    probability: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    weighted_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    billing_cadence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    billing_terms: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    historical_nrr_assumption: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)


class ForecastQuotaCapacity(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_quota_capacity"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", "region", name="pk_forecast_quota_capacity"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False)
    quota_carrying_reps: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    quota_capacity_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expected_bookings_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastRevenueSchedule(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_revenue_schedule"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_revenue_schedule"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    recognized_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    billings: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    deferred_revenue_ending: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    historical_dso: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    expected_collections: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastWorkingCapitalMetrics(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_working_capital_metrics"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", name="pk_forecast_working_capital_metrics"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    dso: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    dpo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    accounts_receivable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastDriverAssumption(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_driver_assumptions"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "effective_period",
            "assumption_name",
            name="pk_forecast_driver_assumptions",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    assumption_name: Mapped[str] = mapped_column(String(256), nullable=False)
    assumption_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actual_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    forecast_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    effective_period: Mapped[date] = mapped_column(Date, nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Forecast")


class ForecastDeferredRevenueWaterfall(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_deferred_revenue_waterfall"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "period",
            name="pk_forecast_deferred_revenue_waterfall",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Forecast")
    period: Mapped[date] = mapped_column(Date, nullable=False)
    beginning_deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    new_billings: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    revenue_recognized: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ending_deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class ForecastOperatingCashFlowBridge(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "forecast_operating_cash_flow_bridge"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "scenario_name",
            "period",
            name="pk_forecast_operating_cash_flow_bridge",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Forecast")
    period: Mapped[date] = mapped_column(Date, nullable=False)
    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    depreciation_and_amortization: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    stock_based_compensation: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    noncash_items: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_accounts_receivable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_deferred_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_accounts_payable: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_prepaids: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    change_in_other_working_capital: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    net_cash_from_operating_activities: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class MrrWaterfall(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "mrr_waterfall"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "period",
            "customer_id",
            "movement_type",
            name="pk_mrr_waterfall",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.customer_id"],
            ondelete="RESTRICT",
            name="fk_mrr_waterfall_customer",
        ),
    )

    period: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    beginning_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    new_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    expansion_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    contraction_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    churn_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    reactivation_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ending_mrr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(64), nullable=False)

    organization = relationship("Organization", back_populates="demo_mrr_waterfall")
