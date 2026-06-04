"""Tenant (organization) model — root for multi-tenant demo finance data."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending", default="pending")
    plan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    billing_customer: Mapped["BillingCustomer | None"] = relationship(
        "BillingCustomer",
        back_populates="organization",
        uselist=False,
    )
    billing_subscriptions: Mapped[list["BillingSubscription"]] = relationship(
        "BillingSubscription",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    demo_customers: Mapped[list["Customer"]] = relationship(
        "Customer",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_opportunities: Mapped[list["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_gl_actuals: Mapped[list["GlActual"]] = relationship(
        "GlActual",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_forecast_gl_detail: Mapped[list["ForecastGlDetail"]] = relationship(
        "ForecastGlDetail",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_warehouse_csv_rows: Mapped[list["WarehouseCsvRow"]] = relationship(
        "WarehouseCsvRow",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_headcount_plan: Mapped[list["HeadcountPlan"]] = relationship(
        "HeadcountPlan",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_vendor_contracts: Mapped[list["VendorContract"]] = relationship(
        "VendorContract",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_sales_quotas: Mapped[list["SalesQuota"]] = relationship(
        "SalesQuota",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_commission_plans: Mapped[list["DemoCommissionPlan"]] = relationship(
        "DemoCommissionPlan",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    demo_mrr_waterfall: Mapped[list["MrrWaterfall"]] = relationship(
        "MrrWaterfall",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
