"""
HRIS-style workforce operating model tables.

Source datasets (uploaded CSVs):
  workforce_employees
  workforce_open_requisitions
  workforce_hiring_ramp_assumptions
  workforce_compensation_bands
  workforce_department_allocation_rules

Derived mart (engine-written or optional export):
  workforce_period_summary — period × department rollups from employee + req logic
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKeyConstraint, Integer, Numeric, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.demo_finance import OrganizationRefMixin, TimestampMixinDemo


class WorkforceEmployee(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "workforce_employees"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "employee_id", name="pk_workforce_employees"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    employee_id: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    sub_department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")
    salary_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    bonus_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    commission_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    equity_sbc_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    benefits_load_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    quota_capacity_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    productivity_ramp_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    months_to_full_productivity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class WorkforceOpenRequisition(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "workforce_open_requisitions"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "req_id", name="pk_workforce_open_requisitions"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    req_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    sub_department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    hiring_manager: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    target_hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    approved_status: Mapped[str] = mapped_column(String(64), nullable=False, default="Approved")
    requisition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    salary_annual_override: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    quota_capacity_arr_override: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class WorkforceHiringRampAssumption(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "workforce_hiring_ramp_assumptions"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "version",
            "department",
            "role",
            "level",
            "month_offset",
            name="pk_workforce_hiring_ramp_assumptions",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    month_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    productivity_pct: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WorkforceCompensationBand(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "workforce_compensation_bands"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "version",
            "department",
            "role",
            "level",
            "region",
            name="pk_workforce_compensation_bands",
        ),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    base_salary_annual: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    bonus_target_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    commission_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    equity_sbc_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    benefits_load_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    default_quota_capacity_arr: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)


class WorkforceDepartmentAllocationRule(OrganizationRefMixin, TimestampMixinDemo, Base):
    __tablename__ = "workforce_department_allocation_rules"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "rule_id", name="pk_workforce_department_allocation_rules"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, default="Forecast")
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    pnl_line: Mapped[str] = mapped_column(String(128), nullable=False)
    allocation_pct: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WorkforcePeriodSummary(OrganizationRefMixin, TimestampMixinDemo, Base):
    """Derived period rollups — payroll is computed, not uploaded."""

    __tablename__ = "workforce_period_summary"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "version", "period", "department", name="pk_workforce_period_summary"),
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    filled_headcount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    planned_hire_headcount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    total_headcount_fte: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    base_payroll_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    bonus_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    commission_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    equity_sbc_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    benefits_load_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_people_cost_monthly: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    quota_capacity_arr: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    productive_quota_capacity_arr: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    derived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
