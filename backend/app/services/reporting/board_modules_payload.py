"""Board Platform module payloads (GTM, Sales, Workforce) from warehouse tables."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workforce import WorkforceEmployee, WorkforceOpenRequisition, WorkforcePeriodSummary
from app.services.dashboard.query_utils import fetch_scenario_rows, fetch_table_rows, preferred_table, table_exists, value_any
from app.services.reporting.period_utils import period_range, to_period
from app.services.workforce.constants import APPROVED_REQ_STATUSES

GTM_CHANNEL_COLORS: tuple[str, ...] = (
    "#1D9E75",
    "#185FA5",
    "#534AB7",
    "#0F6E56",
    "#3B6D11",
    "#BA7517",
    "#E9A23B",
    "#888780",
    "#B4B2A9",
    "#A32D2D",
    "#D85A30",
)

BOARD_WF_DEPARTMENTS: tuple[str, ...] = (
    "Sales",
    "Marketing",
    "R&D",
    "Product",
    "Customer Success",
    "Support",
    "G&A",
)

SALES_REGIONS: tuple[str, ...] = ("West", "EMEA", "East", "Central")


def _money_m(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value) / 1_000_000, 2)


def _num(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _parse_quota_period(raw: Any, *, fallback_year: int) -> str | None:
    if raw is None or raw == "":
        return None
    text = str(raw).strip()
    if len(text) >= 7 and text[4] == "-":
        return text[:7]
    upper = text.upper()
    if upper.startswith("Q") and "-" in upper:
        q_part, year_part = upper.split("-", 1)
        try:
            quarter = int(q_part[1:])
            year = int(year_part)
            month = min(quarter * 3, 12)
            return f"{year:04d}-{month:02d}"
        except ValueError:
            return None
    try:
        parsed = date.fromisoformat(text[:10])
        return to_period(parsed)
    except ValueError:
        pass
    for fmt in ("%b %Y", "%B %Y", "%m/%d/%Y"):
        try:
            from datetime import datetime

            parsed = datetime.strptime(text, fmt)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            continue
    if text.isdigit() and len(text) == 6:
        return f"{text[:4]}-{text[4:]}"
    if text.isdigit() and len(text) == 4:
        return f"{text}-01"
    return f"{fallback_year:04d}-01"


def _fetch_sales_quota_rows(db: Session, organization_id: uuid.UUID, scenario: str) -> list[dict[str, Any]]:
    table = preferred_table(db, scenario, "sales_quotas", fallback="sales_quotas")
    if table is None:
        return []
    return fetch_table_rows(db, table, organization_id)


def _row_get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def build_gtm_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    as_of_period: str,
) -> dict[str, Any]:
    """YTD marketing channel rollup for the board GTM tab."""
    by_channel: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
            "spend": Decimal("0"),
            "pipe": Decimal("0"),
            "won": Decimal("0"),
            "mqls": Decimal("0"),
        }
    )
    for _scenario, period, _table, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario="Actual",
        suffix="marketing_pipeline",
        start_period=start_period,
        end_period=as_of_period,
        as_of_period=as_of_period,
    ):
        channel = str(_row_get(raw, "marketing_channel", "channel") or "Unassigned")
        bucket = by_channel[channel]
        bucket["spend"] += value_any(raw, "marketing_spend", "spend")
        bucket["pipe"] += value_any(raw, "pipeline_arr_created")
        bucket["won"] += value_any(raw, "closed_won_arr", "expected_closed_won_arr")
        bucket["mqls"] += value_any(raw, "mqls")

    if not by_channel:
        return {}

    out: dict[str, Any] = {}
    for idx, (channel, totals) in enumerate(sorted(by_channel.items(), key=lambda item: -float(item[1]["pipe"]))):
        spend = totals["spend"]
        pipe = totals["pipe"]
        won = totals["won"]
        eff = float(pipe / spend) if spend else 0.0
        wr = float(won / pipe * Decimal("100")) if pipe else 0.0
        out[channel] = {
            "spend": _money_m(spend),
            "pipe": _money_m(pipe),
            "won": _money_m(won),
            "mqls": int(totals["mqls"]),
            "eff": round(eff, 1),
            "wr": round(wr, 1),
            "color": GTM_CHANNEL_COLORS[idx % len(GTM_CHANNEL_COLORS)],
        }
    return out


def _aggregate_sales_rows(rows: list[dict[str, Any]], *, fallback_year: int) -> dict[str, Any]:
    monthly: dict[str, dict[str, Any]] = defaultdict(lambda: {"reps": set(), "quota": Decimal("0"), "attained": Decimal("0")})
    regions: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "reps": set(),
            "ytd_quota": Decimal("0"),
            "ytd_attained": Decimal("0"),
            "jun_quota": Decimal("0"),
            "jun_attained": Decimal("0"),
        }
    )
    roles: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"reps": set(), "ytd_quota": Decimal("0"), "ytd_attained": Decimal("0")}
    )
    rep_totals: dict[str, dict[str, Any]] = {}

    for row in rows:
        period = _parse_quota_period(_row_get(row, "quota_period", "period"), fallback_year=fallback_year)
        if not period:
            continue
        rep_id = str(_row_get(row, "rep_id", "owner_rep_id") or "unknown")
        quota = value_any(row, "quota_arr", "quota", "monthly_quota_arr")
        attained = value_any(row, "closed_won_arr_to_date", "closed_won_arr", "attained_arr", "attainment_arr")
        region = str(_row_get(row, "region", "sales_region") or "Unassigned")
        role = str(_row_get(row, "role", "rep_role", "title") or _row_get(row, "segment") or "Rep")
        rep_name = str(_row_get(row, "rep_name", "name") or rep_id)
        sub = str(_row_get(row, "sub_department", "segment") or "")
        annual_q = value_any(row, "annual_quota_arr", "annual_quota")

        bucket = monthly[period]
        bucket["reps"].add(rep_id)
        bucket["quota"] += quota
        bucket["attained"] += attained

        if region in SALES_REGIONS:
            reg = regions[region]
            reg["reps"].add(rep_id)
            reg["ytd_quota"] += quota
            reg["ytd_attained"] += attained

        rol = roles[role]
        rol["reps"].add(rep_id)
        rol["ytd_quota"] += quota
        rol["ytd_attained"] += attained

        rep_key = rep_id
        rep_row = rep_totals.setdefault(
            rep_key,
            {
                "id": rep_id,
                "name": rep_name,
                "role": role,
                "region": region if region in SALES_REGIONS else "East",
                "sub": sub,
                "ytd_q": Decimal("0"),
                "ytd_a": Decimal("0"),
                "annual_q": annual_q,
                "comm": Decimal("0"),
            },
        )
        rep_row["ytd_q"] += quota
        rep_row["ytd_a"] += attained
        if annual_q:
            rep_row["annual_q"] = annual_q

    return {
        "monthly_raw": monthly,
        "regions_raw": regions,
        "roles_raw": roles,
        "rep_totals": rep_totals,
    }


def build_sales_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    as_of_period: str,
    end_period: str,
) -> dict[str, Any]:
    """Sales intelligence block matching board SD shape."""
    year = int(as_of_period[:4])
    actual_rows = _fetch_sales_quota_rows(db, organization_id, "Actual")
    budget_rows = _fetch_sales_quota_rows(db, organization_id, "Budget")

    if not actual_rows and table_exists(db, "sales_quotas"):
        actual_rows = fetch_table_rows(db, "sales_quotas", organization_id)

    actual = _aggregate_sales_rows(actual_rows, fallback_year=year)
    budget = _aggregate_sales_rows(budget_rows, fallback_year=year) if budget_rows else None

    if not actual["monthly_raw"]:
        return {}

    monthly_out: dict[str, Any] = {}
    act_periods = sorted(p for p in actual["monthly_raw"] if start_period <= p <= as_of_period)
    for period in act_periods:
        src = actual["monthly_raw"][period]
        bud = (budget or {}).get("monthly_raw", {}).get(period, {}) if budget else {}
        quota = src["quota"]
        attained = src["attained"]
        bud_quota = bud.get("quota", quota) if bud else quota
        monthly_out[period] = {
            "reps": len(src["reps"]),
            "quota": float(quota),
            "attained": float(attained),
            "pct": float(attained / quota) if quota else 0.0,
            "bud_quota": float(bud_quota),
        }

    regions_out: dict[str, Any] = {}
    for region in SALES_REGIONS:
        src = actual["regions_raw"].get(region)
        if not src or not src["ytd_quota"]:
            continue
        jun_src = actual["monthly_raw"].get(as_of_period, {})
        jun_quota = Decimal("0")
        jun_attained = Decimal("0")
        for row in actual_rows:
            period = _parse_quota_period(_row_get(row, "quota_period", "period"), fallback_year=year)
            if period != as_of_period:
                continue
            if str(_row_get(row, "region", "sales_region") or "") != region:
                continue
            jun_quota += value_any(row, "quota_arr", "quota")
            jun_attained += value_any(row, "closed_won_arr_to_date", "closed_won_arr", "attained_arr")
        regions_out[region] = {
            "reps": len(src["reps"]),
            "ytd_quota": float(src["ytd_quota"]),
            "ytd_attained": float(src["ytd_attained"]),
            "ytd_pct": float(src["ytd_attained"] / src["ytd_quota"]) if src["ytd_quota"] else 0.0,
            "jun_quota": float(jun_quota),
            "jun_attained": float(jun_attained),
        }

    roles_out: dict[str, Any] = {}
    for role, src in actual["roles_raw"].items():
        if not src["ytd_quota"]:
            continue
        roles_out[role] = {
            "reps": len(src["reps"]),
            "ytd_quota": float(src["ytd_quota"]),
            "ytd_attained": float(src["ytd_attained"]),
            "ytd_pct": float(src["ytd_attained"] / src["ytd_quota"]) if src["ytd_quota"] else 0.0,
        }

    pipeline_out: dict[str, Any] = {}
    for _scenario, period, _table, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario="Actual",
        suffix="pipeline_waterfall",
        start_period=start_period,
        end_period=as_of_period,
        as_of_period=as_of_period,
    ):
        created = value_any(raw, "pipeline_arr_created")
        won = value_any(raw, "closed_won_arr", "expected_closed_won_arr")
        lost = value_any(raw, "closed_lost_arr")
        ending = value_any(raw, "ending_pipeline_arr")
        bucket = pipeline_out.setdefault(
            period,
            {"created": Decimal("0"), "won": Decimal("0"), "lost": Decimal("0"), "ending": Decimal("0")},
        )
        bucket["created"] += created
        bucket["won"] += won
        bucket["lost"] += lost
        if ending:
            bucket["ending"] = ending

    for period, vals in pipeline_out.items():
        month_quota = actual["monthly_raw"].get(period, {}).get("quota", Decimal("0"))
        coverage = float(vals["ending"] / month_quota) if month_quota else 0.0
        pipeline_out[period] = {
            "created": float(vals["created"]),
            "won": float(vals["won"]),
            "lost": float(vals["lost"]),
            "ending": float(vals["ending"]),
            "coverage": round(coverage, 1),
        }

    reps_out: list[dict[str, Any]] = []
    for rep in actual["rep_totals"].values():
        ytd_q = rep["ytd_q"]
        ytd_a = rep["ytd_a"]
        pct = float(ytd_a / ytd_q) if ytd_q else 0.0
        comm = ytd_a * Decimal("0.08") if ytd_a else Decimal("0")
        reps_out.append(
            {
                "id": rep["id"],
                "name": rep["name"],
                "role": rep["role"],
                "region": rep["region"],
                "sub": rep["sub"],
                "ytd_q": float(ytd_q),
                "ytd_a": float(ytd_a),
                "pct": pct,
                "annual_q": float(rep["annual_q"]) if rep["annual_q"] else float(ytd_q),
                "comm": float(comm),
            }
        )
    reps_out.sort(key=lambda item: item["pct"], reverse=True)

    budget_fc: dict[str, Any] = {}
    if budget:
        for period in period_range(as_of_period, end_period):
            if period == as_of_period:
                continue
            bud = budget["monthly_raw"].get(period)
            if not bud:
                continue
            budget_fc[period] = {
                "reps": len(bud["reps"]),
                "quota": float(bud["quota"]),
            }

    return {
        "monthly": monthly_out,
        "budget_fc": budget_fc,
        "regions": regions_out,
        "roles": roles_out,
        "pipeline": pipeline_out,
        "reps": reps_out,
    }


def _year_bounds(as_of_period: str) -> tuple[str, str]:
    year = int(as_of_period[:4])
    return f"{year:04d}-01", f"{year:04d}-12"


def build_workforce_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    arr_ending: float | None = None,
) -> dict[str, Any]:
    """Workforce block for board WF_* globals."""
    year_start, year_end = _year_bounds(as_of_period)
    months = period_range(year_start, year_end)
    month_idx = {period: idx for idx, period in enumerate(months)}

    hc_all: dict[str, list[int]] = {dept: [0] * 12 for dept in BOARD_WF_DEPARTMENTS}
    total_hc = [0] * 12
    payroll = [0.0] * 12
    quota_tot = [0.0] * 12
    quota_rmp = [0.0] * 12

    if table_exists(db, "workforce_period_summary"):
        rows = db.scalars(
            select(WorkforcePeriodSummary).where(
                WorkforcePeriodSummary.organization_id == organization_id,
                WorkforcePeriodSummary.version == "Forecast",
                WorkforcePeriodSummary.period >= date(int(year_start[:4]), 1, 1),
                WorkforcePeriodSummary.period <= date(int(year_end[:4]), 12, 1),
            )
        ).all()
        payroll_by_period: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        quota_by_period: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        prod_quota_by_period: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in rows:
            period = to_period(row.period)
            idx = month_idx.get(period)
            if idx is None:
                continue
            dept = row.department
            if dept in hc_all:
                hc_all[dept][idx] = int(row.total_headcount_fte or 0)
            total_hc[idx] += int(row.total_headcount_fte or 0)
            payroll_by_period[period] += row.total_people_cost_monthly or Decimal("0")
            quota_by_period[period] += row.quota_capacity_arr or Decimal("0")
            prod_quota_by_period[period] += row.productive_quota_capacity_arr or Decimal("0")
        for period, idx in month_idx.items():
            payroll[idx] = round(float(payroll_by_period.get(period, Decimal("0"))) / 1_000_000, 2)
            quota_tot[idx] = round(float(quota_by_period.get(period, Decimal("0"))) / 1_000_000, 2)
            quota_rmp[idx] = round(float(prod_quota_by_period.get(period, Decimal("0"))) / 1_000_000, 2)

    close_idx = month_idx.get(as_of_period, 0)
    close_hc = total_hc[close_idx] if total_hc else 0
    dec_hc = total_hc[11] if total_hc else 0

    reqs_out: list[dict[str, Any]] = []
    if table_exists(db, "workforce_open_requisitions"):
        close_date = date(int(as_of_period[:4]), int(as_of_period[5:7]), 1)
        req_rows = db.scalars(
            select(WorkforceOpenRequisition).where(
                WorkforceOpenRequisition.organization_id == organization_id,
                WorkforceOpenRequisition.version == "Forecast",
            )
        ).all()
        for req in req_rows:
            status = (req.approved_status or "").strip().lower()
            if status and status not in APPROVED_REQ_STATUSES:
                continue
            start = req.planned_start_date or req.target_hire_date
            if start is None or start <= close_date:
                continue
            reqs_out.append(
                {
                    "id": req.req_id,
                    "dept": req.department,
                    "role": req.role,
                    "level": req.level or "",
                    "pri": (req.priority or "Medium").title(),
                    "start": to_period(start),
                }
            )
        reqs_out.sort(key=lambda item: item["start"])

    roster_out: list[dict[str, Any]] = []
    if table_exists(db, "workforce_employees"):
        employees = db.scalars(
            select(WorkforceEmployee).where(
                WorkforceEmployee.organization_id == organization_id,
                WorkforceEmployee.version == "Forecast",
            )
        ).all()
        for emp in employees:
            status = (emp.employment_status or "").strip().lower()
            if status and status not in {"active", "on leave", "leave"}:
                continue
            salary = emp.salary_annual or Decimal("0")
            bonus = emp.bonus_annual or Decimal("0")
            comm = emp.commission_annual or Decimal("0")
            sbc = emp.equity_sbc_annual or Decimal("0")
            benefits = salary * (emp.benefits_load_pct or Decimal("0"))
            gaap = salary + bonus + comm + sbc + benefits
            roster_out.append(
                {
                    "id": emp.employee_id,
                    "dept": emp.department,
                    "role": emp.role,
                    "lvl": emp.level or "",
                    "region": emp.region or "Remote",
                    "base": float(salary),
                    "variable": float(bonus + comm),
                    "sbc": float(sbc),
                    "gaap": float(gaap),
                    "quota": float(emp.quota_capacity_arr or 0),
                    "ramp": int(emp.months_to_full_productivity or 0),
                }
            )
        roster_out.sort(key=lambda item: item["gaap"], reverse=True)
        roster_out = roster_out[:24]
        if not close_hc:
            close_hc = len(
                [
                    emp
                    for emp in employees
                    if (emp.employment_status or "").strip().lower() in {"active", "on leave", "leave", ""}
                ]
            )

    arr_per_emp = None
    if arr_ending and close_hc:
        arr_per_emp = int(arr_ending / close_hc)

    return {
        "WF_HC_ALL": hc_all,
        "WF_TOTAL_HC": total_hc,
        "WF_PAYROLL": payroll,
        "WF_QUOTA_TOT": quota_tot,
        "WF_QUOTA_RMP": quota_rmp,
        "WF_REQS": reqs_out,
        "WF_ROSTER": roster_out,
        "summary": {
            "close_hc": close_hc,
            "dec_hc": dec_hc,
            "open_reqs": len(reqs_out),
            "close_payroll_m": payroll[close_idx] if payroll else 0.0,
            "arr_per_employee_k": arr_per_emp,
        },
    }


def build_board_modules_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    start_period: str,
    end_period: str,
    arr_ending: float | None = None,
) -> dict[str, Any]:
    """Aggregate board tab payloads for outlook hydration."""
    gtm = build_gtm_payload(
        db,
        organization_id,
        start_period=start_period,
        as_of_period=as_of_period,
    )
    sd = build_sales_payload(
        db,
        organization_id,
        start_period=start_period,
        as_of_period=as_of_period,
        end_period=end_period,
    )
    workforce = build_workforce_payload(
        db,
        organization_id,
        as_of_period=as_of_period,
        arr_ending=arr_ending,
    )
    return {
        "GTM": gtm,
        "SD": sd,
        "WORKFORCE": workforce,
    }
