"""
Payroll dollars from the GL — the only payroll source for workforce plans, cash and the P&L.

Payroll = Salaries and Wages + Benefits + Payroll Taxes + Commissions (P&L rows only).
The Forecast version covers open months; closed months use Actual GL, matching the outlook.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.services.reporting.gl_income_statement import classify_gl_line, fetch_gl_pl_rows
from app.services.workforce.engine import q_fte, q_money

GL_PAYROLL_SOURCE = "gl_actuals"
CHECK_TOLERANCE = Decimal("1.00")
ALL_TEAMS = "All teams"

WAGES_TYPES = frozenset({"salaries and wages"})
BENEFITS_TYPES = frozenset({"benefits", "payroll taxes"})
COMMISSION_TYPES = frozenset({"commissions"})
PAYROLL_TYPES = WAGES_TYPES | BENEFITS_TYPES | COMMISSION_TYPES

PNL_LINE_BY_GL_LINE = {
    "sm": "sales_and_marketing",
    "rd": "research_and_development",
    "ga": "general_and_administrative",
    "cogs": "cost_of_revenue",
}


@dataclass
class GlPayroll:
    wages: Decimal = Decimal("0")
    benefits: Decimal = Decimal("0")
    commissions: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.wages + self.benefits + self.commissions

    def add(self, expense_type: str, amount: Decimal) -> None:
        if expense_type in WAGES_TYPES:
            self.wages += amount
        elif expense_type in BENEFITS_TYPES:
            self.benefits += amount
        else:
            self.commissions += amount


@dataclass
class GlPayrollSet:
    by_department: dict[tuple[date, str], GlPayroll] = field(default_factory=dict)
    by_pnl_line: dict[tuple[date, str], Decimal] = field(default_factory=dict)

    def periods(self) -> set[date]:
        return {p for p, _ in self.by_department}


def _period(value: Any) -> date | None:
    text = str(value or "")[:7]
    if len(text) != 7:
        return None
    try:
        return date(int(text[:4]), int(text[5:7]), 1)
    except ValueError:
        return None


def build_gl_payroll(rows: Iterable[dict[str, Any]]) -> GlPayrollSet:
    out = GlPayrollSet()
    for raw in rows:
        expense_type = str(raw.get("expense_type") or "").strip().lower()
        if expense_type not in PAYROLL_TYPES:
            continue
        line = classify_gl_line(raw)
        if line is None:
            continue
        period = _period(raw.get("period"))
        if period is None:
            continue
        amount = Decimal(str(raw.get("amount") or 0))
        department = str(raw.get("department") or "").strip() or "Unassigned"
        out.by_department.setdefault((period, department), GlPayroll()).add(expense_type, amount)
        pnl_line = PNL_LINE_BY_GL_LINE.get(line, line)
        out.by_pnl_line[(period, pnl_line)] = out.by_pnl_line.get((period, pnl_line), Decimal("0")) + amount
    return out


def _version_payroll(session: Session, organization_id: uuid.UUID, version: str) -> GlPayrollSet:
    info = getattr(session, "info", None)
    cache = info.setdefault("_gl_payroll", {}) if isinstance(info, dict) else {}
    key = (str(organization_id), version)
    if key not in cache:
        cache[key] = build_gl_payroll(fetch_gl_pl_rows(session, organization_id, version))
    return cache[key]


def gl_payroll(session: Session, organization_id: uuid.UUID, version: str) -> GlPayrollSet:
    """GL payroll for ``version``; Forecast months without Forecast GL payroll use Actual GL."""
    primary = _version_payroll(session, organization_id, version)
    if version != "Forecast":
        return primary
    actual = _version_payroll(session, organization_id, "Actual")
    covered = primary.periods()
    merged = GlPayrollSet(dict(primary.by_department), dict(primary.by_pnl_line))
    for (period, dept), value in actual.by_department.items():
        if period not in covered:
            merged.by_department[(period, dept)] = value
    for (period, line), value in actual.by_pnl_line.items():
        if period not in covered:
            merged.by_pnl_line[(period, line)] = value
    return merged


def gl_payroll_by_period(
    session: Session, organization_id: uuid.UUID, version: str, *, include_commissions: bool = True
) -> dict[date, Decimal]:
    """Monthly GL payroll. Cash views pass ``include_commissions=False``; commissions are their own cash line."""
    payroll = gl_payroll(session, organization_id, version)
    out: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for (period, _), value in payroll.by_department.items():
        out[period] += value.total if include_commissions else value.total - value.commissions
    return dict(out)


def _empty_period_row(period: date, department: str) -> dict[str, Any]:
    zero_fte = q_fte(0)
    return {
        "period": period,
        "department": department,
        "filled_headcount": zero_fte,
        "planned_hire_headcount": zero_fte,
        "total_headcount_fte": zero_fte,
        "quota_capacity_arr": q_money(0),
        "productive_quota_capacity_arr": q_money(0),
    }


def apply_gl_payroll(rows: list[dict[str, Any]], payroll: GlPayrollSet, periods: list[date]) -> list[dict[str, Any]]:
    """Replace people cost on each team row with GL payroll; GL teams without roster rows get a zero-head row."""
    in_range = set(periods)
    by_key = {(r["period"].replace(day=1), r["department"]): dict(r) for r in rows}
    for period, department in payroll.by_department:
        if period in in_range and (period, department) not in by_key:
            by_key[(period, department)] = _empty_period_row(period, department)
    for key, row in by_key.items():
        gl = payroll.by_department.get(key, GlPayroll())
        row.update(
            base_payroll_monthly=q_money(gl.wages),
            bonus_monthly=q_money(0),
            commission_monthly=q_money(gl.commissions),
            equity_sbc_monthly=q_money(0),
            benefits_load_monthly=q_money(gl.benefits),
            total_people_cost_monthly=q_money(gl.total),
        )
    return [by_key[k] for k in sorted(by_key)]


def _fmt(value: Decimal) -> str:
    return f"${value:,.0f}"


def payroll_checks(
    rows: list[dict[str, Any]],
    roster_cost: dict[tuple[date, str], Decimal],
    payroll: GlPayrollSet,
    periods: list[date],
) -> list[dict[str, Any]]:
    """Roster cost vs GL payroll by team over months with GL payroll, plus months with heads but no GL payroll."""
    checks: list[dict[str, Any]] = []
    gl_months = sorted(p for p in payroll.periods() if p in set(periods))
    headed_months = sorted({r["period"] for r in rows if r.get("total_headcount_fte", 0) > 0})
    missing = [p for p in headed_months if p not in set(gl_months)]
    if missing:
        checks.append(
            {
                "period": missing[0],
                "validation_name": "gl_payroll_missing",
                "status": "warning",
                "message": "No GL payroll for " + ", ".join(p.strftime("%Y-%m") for p in missing) + "; payroll shows as zero.",
            }
        )
    if not gl_months:
        return checks

    gl_by_team: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    roster_by_team: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for (period, team), value in payroll.by_department.items():
        if period in gl_months:
            gl_by_team[team] += value.total
    for (period, team), value in roster_cost.items():
        if period in gl_months:
            roster_by_team[team] += value
    span = f"{gl_months[0]:%Y-%m} to {gl_months[-1]:%Y-%m}"
    totals = (ALL_TEAMS, sum(roster_by_team.values(), Decimal("0")), sum(gl_by_team.values(), Decimal("0")))
    teams = [(t, roster_by_team.get(t, Decimal("0")), gl_by_team.get(t, Decimal("0"))) for t in sorted(set(gl_by_team) | set(roster_by_team))]
    for team, roster, gl in [totals, *teams]:
        roster, gl = q_money(roster), q_money(gl)
        variance = q_money(roster - gl)
        checks.append(
            {
                "period": gl_months[0],
                "validation_name": "roster_cost_vs_gl_payroll",
                "status": "pass" if abs(variance) <= CHECK_TOLERANCE else "warning",
                "expected_value": gl,
                "actual_value": roster,
                "variance": variance,
                "message": f"{team}: roster cost {_fmt(roster)} vs GL payroll {_fmt(gl)} ({span}). Reports use GL payroll.",
            }
        )
    return checks
