"""
Board Workforce tab payload.

Head counts come from the employee roster (headcount plan when no roster is loaded), payroll
dollars from the GL only, quota capacity from the headcount plan, open reqs from the
requisitions file and ramp curves from the hiring ramp assumptions. Roster cost is shown only
as a check against GL payroll.

``workforce_board_payload`` is pure so the signed-out demo can be built from the same files.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.workforce import WorkforceHiringRampAssumption, WorkforceOpenRequisition
from app.services.dashboard.query_utils import fetch_table_rows, table_exists
from app.services.reporting.period_utils import period_range, period_to_date, to_period
from app.services.workforce.constants import APPROVED_REQ_STATUSES
from app.services.workforce.gl_payroll import GL_PAYROLL_SOURCE, GlPayroll, GlPayrollSet, gl_payroll
from app.services.workforce.legacy_headcount import LegacyHeadcountSnapshot, load_legacy_headcount_rows
from app.services.workforce.roster import RosterEmployee, load_roster, on_roster

BOARD_WF_DEPARTMENTS: tuple[str, ...] = (
    "Sales",
    "Marketing",
    "R&D",
    "Product",
    "Customer Success",
    "Support",
    "G&A",
)
REQ_TABLES: dict[str, str] = {"Forecast": "forecast_open_requisitions", "Actual": "actual_open_requisitions"}
HEADCOUNT_PLAN_SOURCE = "headcount_plan"


def _ordered(names: Iterable[str]) -> list[str]:
    names = set(names)
    return [d for d in BOARD_WF_DEPARTMENTS if d in names] + sorted(names - set(BOARD_WF_DEPARTMENTS))


def _money(value: Decimal | float | int | None) -> float | None:
    return None if value is None else round(float(value), 2)


def _heads(
    roster: list[RosterEmployee], plan: list[LegacyHeadcountSnapshot], months: list[date]
) -> tuple[dict[str, list[int]], str | None]:
    """Heads by team and month: roster when loaded, otherwise headcount plan ending heads."""
    if any(e.counted for e in roster):
        out: dict[str, list[int]] = defaultdict(lambda: [0] * len(months))
        for employee in roster:
            for idx, month in enumerate(months):
                if on_roster(employee, month):
                    out[employee.department][idx] += 1
        return dict(out), "roster"
    if plan:
        index = {m: i for i, m in enumerate(months)}
        out = defaultdict(lambda: [0] * len(months))
        for row in plan:
            idx = index.get(row.period.replace(day=1))
            if idx is not None:
                out[row.department][idx] = int(row.headcount_ending)
        return dict(out), HEADCOUNT_PLAN_SOURCE
    return {}, None


def _totals(heads: dict[str, list[int]], size: int) -> list[int]:
    return [sum(series[i] for series in heads.values()) for i in range(size)]


def _req_start(row: dict[str, Any]) -> str | None:
    raw = row.get("planned_start_date") or row.get("target_hire_date")
    text = str(raw or "")[:7]
    return text if len(text) == 7 else None


def _open_reqs(reqs: list[dict[str, Any]], as_of_period: str) -> list[dict[str, Any]]:
    out = []
    for row in reqs:
        status = str(row.get("status") or row.get("approved_status") or "").strip().lower()
        approved = str(row.get("approved_flag") or "yes").strip().lower()
        start = _req_start(row)
        if (status and status not in APPROVED_REQ_STATUSES) or approved in {"no", "n", "false"}:
            continue
        if start is None or start <= as_of_period:
            continue
        out.append(
            {
                "id": str(row.get("req_id") or ""),
                "dept": str(row.get("department") or ""),
                "role": str(row.get("role") or ""),
                "level": str(row.get("level") or ""),
                "pri": str(row.get("priority") or "").strip().title(),
                "start": start,
            }
        )
    return sorted(out, key=lambda r: (r["start"], r["id"]))


def _ramp_curves(ramp: list[dict[str, Any]]) -> dict[str, list[float]]:
    by_curve: dict[str, dict[int, float]] = defaultdict(dict)
    for row in ramp:
        by_curve[str(row["ramp_months"])][int(row["month"])] = float(row["pct"])
    return {
        k: [round(v[m] * 100, 1) for m in sorted(v)]
        for k, v in sorted(by_curve.items(), key=lambda kv: float(kv[0]))
    }


def _roster_rows(roster: list[RosterEmployee], close: date) -> list[dict[str, Any]]:
    rows = []
    for e in roster:
        if not on_roster(e, close):
            continue
        rows.append(
            {
                "id": e.employee_id,
                "dept": e.department,
                "role": e.role,
                "lvl": e.level or "",
                "region": e.region or "",
                "status": e.employment_status,
                "base": _money(e.salary_annual or 0),
                "variable": _money((e.bonus_annual or 0) + (e.commission_annual or 0)),
                "sbc": _money(e.equity_sbc_annual or 0),
                "cost": _money(e.annual_cash_cost),
                "quota": _money(e.quota_capacity_arr or 0),
                "ramp": e.months_to_full_productivity,
            }
        )
    order = {d: i for i, d in enumerate(_ordered(r["dept"] for r in rows))}
    return sorted(rows, key=lambda r: (order[r["dept"]], r["id"]))


def _month_payroll(payroll: GlPayrollSet, month: date) -> GlPayroll:
    out = GlPayroll()
    for (period, _), value in payroll.by_department.items():
        if period == month:
            out.wages += value.wages
            out.benefits += value.benefits
            out.commissions += value.commissions
    return out


def _payroll_check(
    roster: list[RosterEmployee], payroll: GlPayrollSet, closed: list[date]
) -> dict[str, Any]:
    """Roster cost vs GL payroll by team over the closed months; reports use GL payroll."""
    gl_months = [m for m in closed if m in payroll.periods()]
    gl: dict[str, Decimal] = defaultdict(Decimal)
    cost: dict[str, Decimal] = defaultdict(Decimal)
    for (period, team), value in payroll.by_department.items():
        if period in gl_months:
            gl[team] += value.total
    for e in roster:
        monthly = e.annual_cash_cost / 12
        for m in gl_months:
            if on_roster(e, m):
                cost[e.department] += monthly
    rows = [
        {"team": t, "roster": _money(cost.get(t, 0)), "gl": _money(gl.get(t, 0)),
         "variance": _money(cost.get(t, Decimal(0)) - gl.get(t, Decimal(0)))}
        for t in _ordered(set(gl) | set(cost))
    ]
    span = f"{gl_months[0]:%Y-%m} to {gl_months[-1]:%Y-%m}" if gl_months else None
    return {"span": span, "rows": rows}


def workforce_board_payload(
    *,
    as_of_period: str,
    roster: list[RosterEmployee],
    budget_roster: list[RosterEmployee],
    plan: list[LegacyHeadcountSnapshot],
    budget_plan: list[LegacyHeadcountSnapshot],
    payroll: GlPayrollSet,
    reqs: list[dict[str, Any]],
    ramp: list[dict[str, Any]],
    roster_source: str | None,
) -> dict[str, Any]:
    year = as_of_period[:4]
    periods = period_range(f"{year}-01", f"{year}-12")
    months = [period_to_date(p) for p in periods]
    close = period_to_date(as_of_period)
    close_idx = periods.index(as_of_period) if as_of_period in periods else len(periods) - 1

    heads, heads_kind = _heads(roster, plan, months)
    budget_heads, _ = _heads(budget_roster, budget_plan, months)
    total = _totals(heads, len(months))
    budget_total = _totals(budget_heads, len(months)) if budget_heads else None

    gl_months = payroll.periods()
    teams = _ordered(team for (period, team) in payroll.by_department if period in set(months))
    by_team = {
        t: [_money(payroll.by_department.get((m, t), GlPayroll()).total) if m in gl_months else None for m in months]
        for t in teams
    }
    month_totals = [_month_payroll(payroll, m) if m in gl_months else None for m in months]
    parts = {
        key: [_money(getattr(t, key)) if t is not None else None for t in month_totals]
        for key in ("wages", "benefits", "commissions")
    }

    plan_index = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for row in plan:
        slot = plan_index[row.period.replace(day=1)]
        slot[0] += row.quota_capacity_arr
        slot[1] += row.productive_quota_capacity_arr
    quota = [_money(plan_index[m][0]) if m in plan_index else None for m in months]
    quota_ramped = [_money(plan_index[m][1]) if m in plan_index else None for m in months]

    open_reqs = _open_reqs(reqs, as_of_period)
    roster_rows = _roster_rows(roster, close) if heads_kind == "roster" else []
    payroll_total = [_money(t.total) if t is not None else None for t in month_totals]

    return {
        "months": periods,
        "close_month": as_of_period,
        "departments": _ordered(heads),
        "heads": {d: heads[d] for d in _ordered(heads)},
        "heads_total": total,
        "heads_budget_total": budget_total,
        "heads_source": roster_source if heads_kind == "roster" else heads_kind,
        "payroll": payroll_total,
        "payroll_by_team": by_team,
        "payroll_parts": parts,
        "payroll_source": GL_PAYROLL_SOURCE,
        "quota": quota,
        "quota_ramped": quota_ramped,
        "quota_source": HEADCOUNT_PLAN_SOURCE if plan else None,
        "reqs": open_reqs,
        "ramp": _ramp_curves(ramp),
        "roster": roster_rows,
        "payroll_check": _payroll_check(roster, payroll, months[: close_idx + 1]) if heads_kind == "roster" else {"span": None, "rows": []},
        "summary": {
            "close_hc": total[close_idx] if heads else None,
            "start_hc": total[0] if heads else None,
            "dec_hc": total[-1] if heads else None,
            "budget_close_hc": budget_total[close_idx] if budget_total else None,
            "open_reqs": len(open_reqs),
            "close_payroll": payroll_total[close_idx],
        },
    }


def _load_reqs(db: Session, organization_id: uuid.UUID, version: str) -> list[dict[str, Any]]:
    table = REQ_TABLES.get(version)
    try:
        if table and table_exists(db, table):
            rows = fetch_table_rows(db, table, organization_id)
            if rows:
                return rows
    except SQLAlchemyError:
        db.rollback()
    uploads = db.scalars(
        select(WorkforceOpenRequisition).where(
            WorkforceOpenRequisition.organization_id == organization_id,
            WorkforceOpenRequisition.version == version,
        )
    )
    return [
        {
            "req_id": r.req_id,
            "department": r.department,
            "role": r.role,
            "level": r.level,
            "priority": r.priority,
            "approved_status": r.approved_status,
            "planned_start_date": r.planned_start_date,
            "target_hire_date": r.target_hire_date,
        }
        for r in uploads
    ]


def _load_ramp(db: Session, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(WorkforceHiringRampAssumption).where(
            WorkforceHiringRampAssumption.organization_id == organization_id,
            WorkforceHiringRampAssumption.department == "*",
            WorkforceHiringRampAssumption.role == "*",
        )
    ).all()
    versions = {r.version for r in rows}
    version = "Forecast" if "Forecast" in versions else next(iter(sorted(versions)), None)
    return [
        {"ramp_months": r.level, "month": r.month_offset + 1, "pct": r.productivity_pct}
        for r in rows
        if r.version == version and r.level
    ]


def build_workforce_payload(db: Session, organization_id: uuid.UUID, *, as_of_period: str) -> dict[str, Any]:
    year = int(as_of_period[:4])
    start, end = date(year, 1, 1), date(year, 12, 1)
    roster, roster_source = load_roster(db, organization_id, "Forecast")
    budget_roster, _ = load_roster(db, organization_id, "Budget")
    return workforce_board_payload(
        as_of_period=to_period(as_of_period),
        roster=roster,
        budget_roster=budget_roster,
        plan=load_legacy_headcount_rows(db, organization_id, scenario="Forecast", start_period=start, end_period=end),
        budget_plan=load_legacy_headcount_rows(db, organization_id, scenario="Budget", start_period=start, end_period=end),
        payroll=gl_payroll(db, organization_id, "Forecast"),
        reqs=_load_reqs(db, organization_id, "Forecast"),
        ramp=_load_ramp(db, organization_id),
        roster_source=roster_source,
    )
