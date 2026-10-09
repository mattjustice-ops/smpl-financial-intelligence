"""Workforce → finance surface integration helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastQuotaCapacity
from app.models.workforce import WorkforceEmployee, WorkforceOpenRequisition, WorkforcePeriodSummary
from app.services.management_pl.gl_hierarchy import GlEntry, resolve_section_and_group
from app.services.reporting.period_utils import to_period
from app.services.workforce import feeds, gl_payroll, legacy_headcount, roster, service
from app.services.workforce.engine import month_start, q_money

WORKFORCE_UPLOAD_KINDS: frozenset[str] = frozenset(
    {
        "workforce_employees",
        "workforce_open_requisitions",
        "workforce_hiring_ramp_assumptions",
        "workforce_compensation_bands",
        "workforce_department_allocation_rules",
    }
)

PAYROLL_GL_GROUPS: frozenset[str] = frozenset(
    {
        "Payroll",
        "Engineering Payroll",
        "Product Payroll",
        "CSM Payroll",
        "Finance Payroll",
        "HR Payroll",
        "Support Payroll",
        "Commissions",
    }
)


def normalize_scenario(scenario: str) -> str:
    s = scenario.strip()
    if s.lower() == "forecast":
        return "Forecast"
    if s.lower() == "budget":
        return "Budget"
    if s.lower() == "actual":
        return "Actual"
    return s


def workforce_source_present(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str = "Forecast",
) -> bool:
    version = normalize_scenario(scenario)
    if roster.roster_present(session, organization_id, version):
        return True
    emp = session.scalar(
        select(func.count())
        .select_from(WorkforceEmployee)
        .where(
            WorkforceEmployee.organization_id == organization_id,
            WorkforceEmployee.version == version,
        )
    )
    if emp and int(emp) > 0:
        return True
    req = session.scalar(
        select(func.count())
        .select_from(WorkforceOpenRequisition)
        .where(
            WorkforceOpenRequisition.organization_id == organization_id,
            WorkforceOpenRequisition.version == version,
        )
    )
    if req and int(req) > 0:
        return True
    return legacy_headcount.legacy_headcount_present(session, organization_id, scenario=version)


def default_recompute_range(*, anchor: date | None = None) -> tuple[date, date]:
    anchor = month_start(anchor or date.today())
    return date(anchor.year, 1, 1), date(anchor.year, 12, 31)


def is_payroll_gl_entry(entry: GlEntry) -> bool:
    if entry.account_group in PAYROLL_GL_GROUPS:
        return True
    if (entry.expense_type or "").strip().lower() in gl_payroll.PAYROLL_TYPES:
        return True
    blob = f"{entry.account_name} {entry.account_group}".lower()
    if "payroll" in blob or "salary" in blob or "salaries" in blob:
        return True
    section, _ = resolve_section_and_group(
        account_name=entry.account_name,
        account_group=entry.account_group,
        category="",
        expense_type=entry.expense_type,
        department=entry.department,
        amount=entry.amount,
    )
    if "commission" in blob and section == "sales_and_marketing":
        return True
    return False


def resolve_payroll_cash_out(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: date,
    scenario: str = "Forecast",
    manual_value: Decimal | None = None,
) -> tuple[Decimal, str]:
    """GL payroll (excluding commissions) for the month; falls back to the cash CSV value when the GL has none."""
    amount = gl_payroll.gl_payroll_by_period(
        session, organization_id, normalize_scenario(scenario), include_commissions=False
    ).get(month_start(period))
    if amount:
        return q_money(amount), gl_payroll.GL_PAYROLL_SOURCE
    if manual_value is not None and manual_value != 0:
        return q_money(manual_value), "forecast_cash_collections"
    return Decimal("0"), "none"


def load_gtm_quota_capacity(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[dict[str, Any]]:
    """Prefer workforce GTM feed; fall back to forecast_quota_capacity CSV table."""
    version = normalize_scenario(scenario)
    if workforce_source_present(session, organization_id, scenario=version):
        rows = feeds.gtm_quota_capacity_feed(
            session,
            organization_id,
            scenario=version,
            start_period=start_period,
            end_period=end_period,
        )
        if rows and any((r.get("productive_quota_capacity_arr") or 0) != 0 for r in rows):
            return rows

    legacy = session.scalars(
        select(ForecastQuotaCapacity).where(
            ForecastQuotaCapacity.organization_id == organization_id,
            ForecastQuotaCapacity.version == version,
            ForecastQuotaCapacity.period >= month_start(start_period),
            ForecastQuotaCapacity.period <= month_start(end_period),
        )
    )
    return [
        {
            "period": row.period,
            "region": row.region,
            "quota_carrying_reps": row.quota_carrying_reps or Decimal("0"),
            "quota_capacity_arr": row.quota_capacity_arr or Decimal("0"),
            "productive_quota_capacity_arr": row.quota_capacity_arr or Decimal("0"),
            "expected_bookings_arr": row.expected_bookings_arr,
            "source": "forecast_quota_capacity",
        }
        for row in legacy
    ]


def auto_recompute_after_upload(
    session: Session,
    organization_id: uuid.UUID,
    kind: str,
    *,
    scenario: str = "Forecast",
    sync_legacy_headcount: bool = True,
) -> dict[str, Any] | None:
    if kind not in WORKFORCE_UPLOAD_KINDS:
        return None
    start, end = default_recompute_range()
    plan = service.build_workforce_plan(
        session,
        organization_id,
        scenario=scenario,
        start_period=start,
        end_period=end,
        persist=True,
    )
    legacy_rows = 0
    if sync_legacy_headcount:
        legacy_rows = feeds.sync_legacy_headcount_plan(
            session,
            organization_id,
            scenario=scenario,
            start_period=start,
            end_period=end,
        )
    return {
        "periods_computed": len(plan.period_summary),
        "legacy_headcount_rows_synced": legacy_rows,
        "start_period": start.isoformat(),
        "end_period": end.isoformat(),
    }


def load_headcount_from_workforce_summary(
    session: Session,
    organization_id: uuid.UUID,
    start: str,
    end: str,
    *,
    scenarios: tuple[str, ...] = ("Actual", "Forecast", "Budget"),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version in scenarios:
        for row in service.load_persisted_summary(
            session,
            organization_id,
            scenario=version,
            start_period=date(int(start[:4]), int(start[5:7]), 1),
            end_period=date(int(end[:4]), int(end[5:7]), 1),
        ):
            period = to_period(row.period)
            if period < start or period > end:
                continue
            rows.append(
                {
                    "scenario": version,
                    "period": period,
                    "department": row.department,
                    "headcount": row.total_headcount_fte,
                    "open_roles": row.planned_hire_headcount,
                    "hiring_plan": row.planned_hire_headcount,
                    "total_people_cost_monthly": row.total_people_cost_monthly,
                    "source_table": "workforce_period_summary",
                }
            )
    return rows
