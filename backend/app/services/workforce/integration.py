"""Workforce → finance surface integration helpers."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastQuotaCapacity
from app.models.workforce import WorkforceEmployee, WorkforceOpenRequisition, WorkforcePeriodSummary
from app.services.management_pl.gl_hierarchy import GlEntry, resolve_section_and_group
from app.services.reporting.period_utils import to_period
from app.services.workforce import feeds, legacy_headcount, service
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

OPEX_IS_KEYS: tuple[str, ...] = (
    "sales_and_marketing",
    "research_and_development",
    "general_and_administrative",
    "customer_success",
    "cost_of_revenue",
)

PNL_LINE_TO_IS_KEY: dict[str, str] = {
    "sales_and_marketing": "sales_and_marketing",
    "sales_and_marketing_expense": "sales_and_marketing",
    "sm": "sales_and_marketing",
    "sales_marketing": "sales_and_marketing",
    "research_and_development": "research_and_development",
    "r_and_d": "research_and_development",
    "rd": "research_and_development",
    "general_and_administrative": "general_and_administrative",
    "g_and_a": "general_and_administrative",
    "ga": "general_and_administrative",
    "customer_success": "customer_success",
    "cost_of_revenue": "cost_of_revenue",
    "cogs": "cost_of_revenue",
}

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


def pnl_line_to_is_key(pnl_line: str) -> str | None:
    key = pnl_line.strip().lower().replace("&", "and").replace(" ", "_")
    key = key.replace("__", "_")
    return PNL_LINE_TO_IS_KEY.get(key)


def workforce_source_present(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str = "Forecast",
) -> bool:
    version = normalize_scenario(scenario)
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


def pnl_overlay_by_period(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> dict[str, dict[str, Decimal]]:
    """Period (YYYY-MM) → income-statement key → derived people cost."""
    lines = feeds.pnl_people_cost_lines(
        session,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
    overlay: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for row in lines:
        period = row["period"]
        ps = to_period(period if isinstance(period, date) else str(period))
        raw_line = str(row.get("pnl_line") or "")
        is_key = pnl_line_to_is_key(raw_line) or pnl_line_to_is_key(raw_line.lower().replace(" ", "_"))
        if not is_key:
            continue
        overlay[ps][is_key] += q_money(row.get("amount") or 0)
    return {p: dict(v) for p, v in overlay.items()}


def is_payroll_gl_entry(entry: GlEntry) -> bool:
    if entry.account_group in PAYROLL_GL_GROUPS:
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


def _entry_section(entry: GlEntry) -> str:
    section, _ = resolve_section_and_group(
        account_name=entry.account_name,
        account_group=entry.account_group,
        category="",
        expense_type=entry.expense_type,
        department=entry.department,
        amount=entry.amount,
    )
    return section


def exclude_payroll_gl_entries(entries: list[GlEntry], open_periods: set[str]) -> list[GlEntry]:
    if not open_periods:
        return entries
    return [e for e in entries if e.period not in open_periods or not is_payroll_gl_entry(e)]


def non_payroll_gl_by_period_section(
    entries: list[GlEntry],
    open_periods: set[str],
) -> dict[str, dict[str, Decimal]]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for entry in entries:
        if entry.period not in open_periods or is_payroll_gl_entry(entry):
            continue
        totals[entry.period][_entry_section(entry)] += abs(entry.amount)
    return {p: dict(v) for p, v in totals.items()}


def _recalc_is_row(row: dict[str, Decimal]) -> None:
    rev = row.get("revenue", Decimal("0"))
    cogs = row.get("cost_of_revenue", Decimal("0"))
    gp = rev - cogs
    row["gross_profit"] = gp
    opex = sum(row.get(k, Decimal("0")) for k in OPEX_IS_KEYS if k != "cost_of_revenue")
    row["total_opex"] = opex
    row["ebitda"] = gp - opex


def apply_workforce_pnl_to_income_map(
    income_map: dict[str, dict[str, Decimal]],
    overlay: dict[str, dict[str, Decimal]],
    open_periods: set[str],
    *,
    non_payroll_gl: dict[str, dict[str, Decimal]] | None = None,
) -> dict[str, dict[str, Decimal]]:
    merged = {p: dict(v) for p, v in income_map.items()}
    section_by_is = {
        "sales_and_marketing": "sales_and_marketing",
        "research_and_development": "research_and_development",
        "general_and_administrative": "general_and_administrative",
        "customer_success": "customer_success",
        "cost_of_revenue": "cogs",
    }
    for period in open_periods:
        row = merged.setdefault(period, {})
        for is_key, wf_amt in overlay.get(period, {}).items():
            np_gl = Decimal("0")
            if non_payroll_gl:
                section = section_by_is.get(is_key, is_key)
                np_gl = non_payroll_gl.get(period, {}).get(section, Decimal("0"))
            row[is_key] = abs(wf_amt) + abs(np_gl)
        _recalc_is_row(row)
    return merged


def resolve_payroll_cash_out(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: date,
    scenario: str = "Forecast",
    manual_value: Decimal | None = None,
) -> tuple[Decimal, str]:
    """Workforce-derived payroll cash out; fall back to manual CSV value."""
    if workforce_source_present(session, organization_id, scenario=scenario):
        rows = feeds.cash_payroll_outflow(
            session,
            organization_id,
            scenario=scenario,
            start_period=month_start(period),
            end_period=month_start(period),
        )
        if rows:
            return q_money(rows[0].get("payroll_cash_out") or 0), "workforce_derived"
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
