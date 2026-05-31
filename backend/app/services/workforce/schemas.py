"""API schemas for workforce operating intelligence."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.services.reporting.validation_service import ValidationCheck


class WorkforcePeriodDepartmentRow(BaseModel):
    period: date
    department: str
    headcount_beginning_fte: Decimal = Decimal("0")
    new_hires_fte: Decimal = Decimal("0")
    attrition_fte: Decimal = Decimal("0")
    headcount_ending_fte: Decimal = Decimal("0")
    filled_headcount: Decimal
    planned_hire_headcount: Decimal
    total_headcount_fte: Decimal
    base_payroll_monthly: Decimal
    bonus_monthly: Decimal
    commission_monthly: Decimal
    equity_sbc_monthly: Decimal
    benefits_load_monthly: Decimal
    total_people_cost_monthly: Decimal
    quota_capacity_arr: Decimal
    productive_quota_capacity_arr: Decimal


class WorkforcePnlAllocationRow(BaseModel):
    period: date
    pnl_line: str
    amount: Decimal
    departments: list[str] = Field(default_factory=list)


class WorkforceOperatingMetrics(BaseModel):
    period: date
    revenue: Decimal | None = None
    arr: Decimal | None = None
    filled_headcount_fte: Decimal = Decimal("0")
    planned_hire_headcount_fte: Decimal = Decimal("0")
    planned_starts_fte: Decimal = Decimal("0")
    total_headcount_fte: Decimal
    revenue_per_employee: Decimal | None = None
    arr_per_employee: Decimal | None = None
    total_people_cost_monthly: Decimal
    burn_multiple: Decimal | None = None


class WorkforceCapacityRow(BaseModel):
    period: date
    department: str
    quota_carrying_reps_fte: Decimal
    quota_capacity_arr: Decimal
    productive_quota_capacity_arr: Decimal
    expected_bookings_arr: Decimal | None = None


class WorkforceValidationRow(BaseModel):
    scenario: str
    period: date
    validation_name: str
    status: Literal["pass", "warning", "fail"]
    expected_value: Decimal | None = None
    actual_value: Decimal | None = None
    variance: Decimal | None = None
    message: str | None = None


class WorkforceValidationResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    status: Literal["pass", "warning", "fail"]
    checks: list[ValidationCheck] = Field(default_factory=list)
    failed_count: int = 0
    warning_count: int = 0
    passed_count: int = 0


class WorkforcePlanResponse(BaseModel):
    organization_id: str
    scenario: str
    start_period: date
    end_period: date
    departments: list[str]
    period_summary: list[WorkforcePeriodDepartmentRow]
    pnl_allocations: list[WorkforcePnlAllocationRow]
    gtm_capacity: list[WorkforceCapacityRow]
    operating_metrics: list[WorkforceOperatingMetrics]
    validations: list[WorkforceValidationRow]
    data_sources: list[str]
