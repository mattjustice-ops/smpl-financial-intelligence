"""Board Platform module payloads (GTM, Sales, Workforce) from warehouse tables."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, fetch_table_rows, preferred_table, table_exists, value_any
from app.services.reporting.board_workforce import build_workforce_payload
from app.services.reporting.period_utils import period_range, to_period

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

# Opportunity types that make up the sales pipeline; Churn and Contraction rows are retention risk, not pipeline.
PIPELINE_BOOKING_TYPES: tuple[str, ...] = ("New Business", "Expansion", "Reactivation")
PIPELINE_COVERAGE_TYPE = "New Business"


def _money_m(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value) / 1_000_000, 2)


def _loaded(row: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        if row.get(key) not in (None, ""):
            return value_any(row, key)
    return None


def _parse_quota_period(raw: Any) -> str | None:
    """Month key for a quota row; None when the value does not name a month."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, date):
        return to_period(raw)
    text = str(raw).strip()
    if len(text) >= 7 and text[4] == "-" and text[:4].isdigit() and text[5:7].isdigit():
        return text[:7]
    from datetime import datetime

    for fmt in ("%b %Y", "%B %Y", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            continue
    if text.isdigit() and len(text) == 6:
        return f"{text[:4]}-{text[4:]}"
    return None


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
    """YTD marketing channel volumes for the board GTM tab; spend is by GL account (TS_DATA ``gl_programs``)."""
    by_channel: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
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
        bucket["pipe"] += value_any(raw, "pipeline_arr_created")
        bucket["won"] += value_any(raw, "closed_won_arr", "expected_closed_won_arr")
        bucket["mqls"] += value_any(raw, "mqls")

    if not by_channel:
        return {}

    out: dict[str, Any] = {}
    for idx, (channel, totals) in enumerate(sorted(by_channel.items(), key=lambda item: -float(item[1]["pipe"]))):
        pipe = totals["pipe"]
        won = totals["won"]
        wr = round(float(won / pipe * Decimal("100")), 1) if pipe else None
        out[channel] = {
            "pipe": _money_m(pipe),
            "won": _money_m(won),
            "mqls": int(totals["mqls"]),
            "wr": wr,
            "color": GTM_CHANNEL_COLORS[idx % len(GTM_CHANNEL_COLORS)],
        }
    return out


_QUOTA_KEYS = ("monthly_quota_arr", "quota_arr", "quota")
_ATTAINED_KEYS = ("quota_attainment_actual_arr", "closed_won_arr_to_date", "closed_won_arr", "attained_arr", "attainment_arr")


def _aggregate_sales_rows(rows: list[dict[str, Any]], *, close_period: str) -> dict[str, Any]:
    monthly: dict[str, dict[str, Any]] = defaultdict(lambda: {"reps": set(), "quota": Decimal("0"), "attained": Decimal("0")})
    regions: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "reps": set(),
            "ytd_quota": Decimal("0"),
            "ytd_attained": Decimal("0"),
            "close_quota": None,
            "close_attained": None,
        }
    )
    roles: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"reps": set(), "ytd_quota": Decimal("0"), "ytd_attained": Decimal("0")}
    )
    rep_totals: dict[str, dict[str, Any]] = {}

    for row in rows:
        period = _parse_quota_period(_row_get(row, "quota_period", "period"))
        if not period or period > close_period:
            continue
        rep_id = str(_row_get(row, "employee_id", "rep_id", "owner_rep_id") or "Unassigned")
        quota = value_any(row, *_QUOTA_KEYS)
        attained = value_any(row, *_ATTAINED_KEYS)
        region = str(_row_get(row, "region", "sales_region") or "Unassigned")
        role = str(_row_get(row, "role", "rep_role", "title") or "Unassigned")
        rep_name = str(_row_get(row, "rep_name", "name") or rep_id)
        sub = str(_row_get(row, "sub_department", "segment") or "")
        annual_q = _loaded(row, "annual_quota_arr", "annual_quota")

        bucket = monthly[period]
        bucket["reps"].add(rep_id)
        bucket["quota"] += quota
        bucket["attained"] += attained

        reg = regions[region]
        reg["reps"].add(rep_id)
        reg["ytd_quota"] += quota
        reg["ytd_attained"] += attained
        if period == close_period:
            reg["close_quota"] = (reg["close_quota"] or Decimal("0")) + quota
            reg["close_attained"] = (reg["close_attained"] or Decimal("0")) + attained

        rol = roles[role]
        rol["reps"].add(rep_id)
        rol["ytd_quota"] += quota
        rol["ytd_attained"] += attained

        rep_row = rep_totals.setdefault(
            rep_id,
            {
                "id": rep_id,
                "name": rep_name,
                "role": role,
                "region": region,
                "sub": sub,
                "ytd_q": Decimal("0"),
                "ytd_a": Decimal("0"),
                "annual_q": annual_q,
            },
        )
        rep_row["ytd_q"] += quota
        rep_row["ytd_a"] += attained
        if annual_q is not None:
            rep_row["annual_q"] = annual_q

    return {
        "monthly_raw": monthly,
        "regions_raw": regions,
        "roles_raw": roles,
        "rep_totals": rep_totals,
    }


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _pct(num: Decimal | None, den: Decimal | None) -> float | None:
    return float(num / den) if num is not None and den else None


def _pipeline_by_period(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: str,
    end_period: str,
    as_of_period: str,
) -> tuple[dict[str, Any], list[str]]:
    """Loaded pipeline waterfall rows by period: per-type values plus booking-type totals (None when a part is not loaded)."""
    by_period: dict[str, dict[str, dict[str, Decimal | None]]] = defaultdict(dict)
    for _scenario, period, _table, raw in fetch_scenario_rows(
        db,
        organization_id,
        scenario=scenario,
        suffix="pipeline_waterfall",
        start_period=start_period,
        end_period=end_period,
        as_of_period=as_of_period,
    ):
        otype = str(_row_get(raw, "opportunity_type") or "Unassigned")
        by_period[period][otype] = {
            "beginning": _loaded(raw, "beginning_pipeline_arr"),
            "created": _loaded(raw, "new_pipeline_created", "pipeline_arr_created"),
            "won": _loaded(raw, "closed_won_arr"),
            "lost": _loaded(raw, "closed_lost_arr"),
            "slipped": _loaded(raw, "slipped_arr", "slipped_pipeline_arr"),
            "ending": _loaded(raw, "ending_pipeline_arr"),
            "coverage": _loaded(raw, "pipeline_coverage"),
        }

    types_seen: set[str] = set()
    out: dict[str, Any] = {}
    for period in sorted(by_period):
        rows = by_period[period]
        booking = [rows[t] for t in PIPELINE_BOOKING_TYPES if t in rows]
        types_seen.update(t for t in PIPELINE_BOOKING_TYPES if t in rows)

        def total(key: str) -> float | None:
            vals = [r[key] for r in booking]
            if not vals or any(v is None for v in vals):
                return None
            return float(sum(vals, Decimal("0")))

        cov_row = rows.get(PIPELINE_COVERAGE_TYPE) or {}
        out[period] = {
            "beginning": total("beginning"),
            "created": total("created"),
            "won": total("won"),
            "lost": total("lost"),
            "slipped": total("slipped"),
            "ending": total("ending"),
            "coverage": _f(cov_row.get("coverage")),
            "by_type": {t: {k: _f(v) for k, v in vals.items()} for t, vals in sorted(rows.items())},
        }
    return out, [t for t in PIPELINE_BOOKING_TYPES if t in types_seen]


def build_sales_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    as_of_period: str,
    end_period: str,
) -> dict[str, Any]:
    """Sales intelligence block matching board SD shape, from loaded quota and pipeline rows only."""
    actual_rows = _fetch_sales_quota_rows(db, organization_id, "Actual")
    budget_rows = _fetch_sales_quota_rows(db, organization_id, "Budget")

    if not actual_rows and table_exists(db, "sales_quotas"):
        actual_rows = fetch_table_rows(db, "sales_quotas", organization_id)

    actual = _aggregate_sales_rows(actual_rows, close_period=as_of_period)
    budget = _aggregate_sales_rows(budget_rows, close_period=end_period) if budget_rows else None

    if not actual["monthly_raw"]:
        return {}

    monthly_out: dict[str, Any] = {}
    act_periods = sorted(p for p in actual["monthly_raw"] if start_period <= p <= as_of_period)
    for period in act_periods:
        src = actual["monthly_raw"][period]
        bud = budget["monthly_raw"].get(period) if budget else None
        monthly_out[period] = {
            "reps": len(src["reps"]),
            "quota": float(src["quota"]),
            "attained": float(src["attained"]),
            "pct": _pct(src["attained"], src["quota"]),
            "bud_quota": float(bud["quota"]) if bud else None,
        }

    regions_out: dict[str, Any] = {}
    for region, src in sorted(actual["regions_raw"].items()):
        regions_out[region] = {
            "reps": len(src["reps"]),
            "ytd_quota": float(src["ytd_quota"]),
            "ytd_attained": float(src["ytd_attained"]),
            "ytd_pct": _pct(src["ytd_attained"], src["ytd_quota"]),
            "close_quota": _f(src["close_quota"]),
            "close_attained": _f(src["close_attained"]),
        }

    roles_out: dict[str, Any] = {}
    for role, src in sorted(actual["roles_raw"].items()):
        roles_out[role] = {
            "reps": len(src["reps"]),
            "ytd_quota": float(src["ytd_quota"]),
            "ytd_attained": float(src["ytd_attained"]),
            "ytd_pct": _pct(src["ytd_attained"], src["ytd_quota"]),
        }

    pipeline_out, pipeline_types = _pipeline_by_period(
        db,
        organization_id,
        scenario="Actual",
        start_period=start_period,
        end_period=as_of_period,
        as_of_period=as_of_period,
    )
    fc_periods = period_range(as_of_period, end_period)[1:]
    pipeline_fc: dict[str, Any] = {}
    if fc_periods:
        pipeline_fc, _ = _pipeline_by_period(
            db,
            organization_id,
            scenario="Forecast",
            start_period=fc_periods[0],
            end_period=fc_periods[-1],
            as_of_period=as_of_period,
        )

    reps_out: list[dict[str, Any]] = []
    for rep in actual["rep_totals"].values():
        reps_out.append(
            {
                "id": rep["id"],
                "name": rep["name"],
                "role": rep["role"],
                "region": rep["region"],
                "sub": rep["sub"],
                "ytd_q": float(rep["ytd_q"]),
                "ytd_a": float(rep["ytd_a"]),
                "pct": _pct(rep["ytd_a"], rep["ytd_q"]),
                "annual_q": _f(rep["annual_q"]),
                "comm": None,
            }
        )
    reps_out.sort(key=lambda item: (item["pct"] is None, -(item["pct"] or 0.0)))

    return {
        "monthly": monthly_out,
        "quota_through": act_periods[-1] if act_periods else None,
        "regions": regions_out,
        "roles": roles_out,
        "pipeline": pipeline_out,
        "pipeline_fc": pipeline_fc,
        "pipeline_types": pipeline_types,
        "reps": reps_out,
    }


def build_board_modules_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
    start_period: str,
    end_period: str,
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
    workforce = build_workforce_payload(db, organization_id, as_of_period=as_of_period)
    return {
        "GTM": gtm,
        "SD": sd,
        "WORKFORCE": workforce,
    }
