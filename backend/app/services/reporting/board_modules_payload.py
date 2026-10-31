"""Board Platform module payloads (GTM, Sales, Workforce) from warehouse tables."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_scenario_rows, fetch_table_rows, preferred_table, table_exists, value_any
from app.services.reporting.board_workforce import build_workforce_payload
from app.services.reporting.vendor_usage import build_vendor_usage_payload
from app.services.reporting.fiscal_year import forecast_periods_after_close
from app.services.reporting.period_utils import to_period

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


MILLION = Decimal("1000000")


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
    """YTD marketing channel volumes for the board GTM tab; spend is by GL account (TS_DATA ``gl_programs``).

    ``pipe`` and ``won`` are unrounded $M: the board adds channels up, and rounded channels would not foot.
    """
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
            "pipe": float(pipe / MILLION),
            "won": float(won / MILLION),
            "mqls": int(totals["mqls"]),
            "wr": wr,
            "color": GTM_CHANNEL_COLORS[idx % len(GTM_CHANNEL_COLORS)],
        }
    return out


def _gtm_history_start(start_period: str, as_of_period: str) -> str:
    """Year-ago January, so a month and a year-to-date comparison can see the prior year."""
    prior = f"{int(as_of_period[:4]) - 1}-01"
    return prior if prior < start_period else start_period


def build_gtm_months(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    as_of_period: str,
    end_period: str,
) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """Channel pipeline, closed won, and MQLs by month and scenario. Amounts are dollars.

    The board GTM tab keeps the year-to-date channel map. Executive discussion sums these
    months for whichever comparison is selected.
    """
    windows = {
        "Actual": (_gtm_history_start(start_period, as_of_period), as_of_period, as_of_period),
        "Budget": (start_period, end_period, as_of_period),
        "Forecast": (start_period, end_period, as_of_period),
    }
    out: dict[str, dict[str, dict[str, dict[str, float | int]]]] = {}
    for scenario, (first, last, as_of) in windows.items():
        by_period: dict[str, dict[str, dict[str, Decimal]]] = defaultdict(
            lambda: defaultdict(lambda: {"pipe": Decimal("0"), "won": Decimal("0"), "mqls": Decimal("0")})
        )
        for _scenario, period, _table, raw in fetch_scenario_rows(
            db,
            organization_id,
            scenario=scenario,
            suffix="marketing_pipeline",
            start_period=first,
            end_period=last,
            as_of_period=as_of,
        ):
            if scenario == "Actual" and period > as_of_period:
                continue
            if scenario == "Forecast" and period <= as_of_period:
                continue
            channel = str(_row_get(raw, "marketing_channel", "channel") or "Unassigned")
            bucket = by_period[period][channel]
            bucket["pipe"] += value_any(raw, "pipeline_arr_created")
            bucket["won"] += value_any(raw, "closed_won_arr", "expected_closed_won_arr")
            bucket["mqls"] += value_any(raw, "mqls")
        out[scenario] = {
            period: {
                channel: {
                    "pipe": float(totals["pipe"]),
                    "won": float(totals["won"]),
                    "mqls": int(totals["mqls"]),
                }
                for channel, totals in channels.items()
            }
            for period, channels in by_period.items()
        }
    return out


_QUOTA_KEYS = ("ramped_monthly_quota_arr", "monthly_quota_arr", "quota_arr", "quota")
_ATTAINED_KEYS = ("quota_attainment_actual_arr", "closed_won_arr_to_date", "closed_won_arr", "attained_arr", "attainment_arr")
NON_QUOTA_TYPE = "non-quota"
TEAM_QUOTA_TYPE = "Bookings ARR"
COMMISSION_PAYOUT_SUFFIXES: tuple[str, ...] = ("commission_payouts", "renewal_commissions")
COMMISSION_PAY_PLAN = "commission"


def _quota_type(row: dict[str, Any]) -> str:
    return str(_row_get(row, "quota_type") or "")


def _carries_quota(row: dict[str, Any]) -> bool:
    """A row whose quota type is Non-Quota is not a quota carrier; without a quota type, a carrier has a quota."""
    kind = _quota_type(row)
    if kind:
        return kind.lower() != NON_QUOTA_TYPE
    return (_loaded(row, "annual_quota_arr", "annual_quota") or Decimal("0")) > 0 or value_any(row, *_QUOTA_KEYS) > 0


def _aggregate_sales_rows(rows: list[dict[str, Any]], *, close_period: str) -> dict[str, Any]:
    """Quota carriers only, on ramped quota. Monthly and regional totals are the closers (Bookings ARR quota)
    when the file names quota types, since pipeline and expansion quotas measure different things; roles and reps
    keep every quota type."""
    rows = [r for r in rows if _carries_quota(r)]
    team_type = TEAM_QUOTA_TYPE if any(_quota_type(r) == TEAM_QUOTA_TYPE for r in rows) else None
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
        lambda: {"reps": set(), "ytd_quota": Decimal("0"), "ytd_attained": Decimal("0"), "quota_type": None}
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
        kind = _quota_type(row) or None

        if team_type is None or kind == team_type:
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
        rol["quota_type"] = kind

        rep_row = rep_totals.setdefault(
            rep_id,
            {
                "id": rep_id,
                "name": rep_name,
                "role": role,
                "region": region,
                "sub": sub,
                "quota_type": kind,
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
        "team_type": team_type,
    }


def _commission_paid_by_rep(
    db: Session, organization_id: uuid.UUID, *, start_period: str, as_of_period: str
) -> dict[str, Decimal] | None:
    """Commission paid per rep ID through the close (commission and renewal commission payouts); None when no
    payout table is loaded."""
    tables = [f"actual_{s}" for s in COMMISSION_PAYOUT_SUFFIXES if table_exists(db, f"actual_{s}")]
    if not tables:
        return None
    paid: dict[str, Decimal] = defaultdict(Decimal)
    for table in tables:
        for row in fetch_table_rows(db, table, organization_id):
            period = _parse_quota_period(_row_get(row, "period"))
            rep_id = _row_get(row, "rep_id", "employee_id")
            if period and rep_id and start_period <= period <= as_of_period:
                paid[str(rep_id)] += value_any(row, "commission_amount")
    return paid


def _commission_plan_reps(db: Session, organization_id: uuid.UUID) -> set[str]:
    """Employee IDs the Actual roster puts on a commission pay plan (empty when the roster names no pay plans)."""
    table = preferred_table(db, "Actual", "employees")
    if table is None:
        return set()
    return {
        str(_row_get(row, "employee_id"))
        for row in fetch_table_rows(db, table, organization_id)
        if str(_row_get(row, "pay_plan") or "").strip().lower() == COMMISSION_PAY_PLAN and _row_get(row, "employee_id")
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
            "quota_type": src["quota_type"],
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
    fc_periods = forecast_periods_after_close(as_of_period, end_period)
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

    paid = _commission_paid_by_rep(db, organization_id, start_period=start_period, as_of_period=as_of_period)
    # A rep on a commission plan with no payouts yet was paid $0; any other rep without payouts has no commission.
    on_plan = _commission_plan_reps(db, organization_id) if paid is not None else set()
    reps_out: list[dict[str, Any]] = []
    for rep in actual["rep_totals"].values():
        comm = paid.get(rep["id"], Decimal("0") if rep["id"] in on_plan else None) if paid is not None else None
        reps_out.append(
            {
                "id": rep["id"],
                "name": rep["name"],
                "role": rep["role"],
                "region": rep["region"],
                "sub": rep["sub"],
                "quota_type": rep["quota_type"],
                "ytd_q": float(rep["ytd_q"]),
                "ytd_a": float(rep["ytd_a"]),
                "pct": _pct(rep["ytd_a"], rep["ytd_q"]),
                "annual_q": _f(rep["annual_q"]),
                "comm": _f(comm),
            }
        )
    reps_out.sort(key=lambda item: (item["pct"] is None, -(item["pct"] or 0.0)))

    return {
        "team_quota_type": actual["team_type"],
        "commission_loaded": paid is not None,
        "monthly": monthly_out,
        "quota_through": act_periods[-1] if act_periods else None,
        "regions": regions_out,
        "roles": roles_out,
        "pipeline": pipeline_out,
        "pipeline_fc": pipeline_fc,
        "pipeline_types": pipeline_types,
        "reps": reps_out,
    }


_REVENUE_MIX_TIE = 1.0
_CONCENTRATION = ((1, "Largest customer"), (5, "Top 5 customers"), (10, "Top 10 customers"), (25, "Top 25 customers"))


def _cents(value: float) -> float:
    return round(float(value) + 0.0, 2)


def revenue_mix_views(
    by_customer: dict[str, float],
    attributes: dict[str, tuple[str | None, str | None]],
    gl_total: float | None,
) -> dict[str, Any] | None:
    """June cuts of recognized revenue. A cut is included only when every dollar is tagged and the rows add to the income statement."""
    if gl_total is None or not by_customer:
        return None
    total = sum(by_customer.values())
    if abs(total - float(gl_total)) > _REVENUE_MIX_TIE:
        return None

    def grouped(index: int) -> list[dict[str, Any]] | None:
        buckets: dict[str, float] = defaultdict(float)
        for customer_id, amount in by_customer.items():
            raw = attributes.get(customer_id)
            label = ""
            if raw is not None and raw[index] is not None:
                label = str(raw[index]).strip()
            if not label:
                return None
            buckets[label] += amount
        rows = [{"label": label, "amount": _cents(amount)} for label, amount in buckets.items()]
        rows.sort(key=lambda row: (-row["amount"], row["label"]))
        if abs(sum(row["amount"] for row in rows) - _cents(total)) > _REVENUE_MIX_TIE:
            return None
        return rows

    views: dict[str, list[dict[str, Any]]] = {}
    industry = grouped(0)
    segment = grouped(1)
    if industry:
        views["industry"] = industry
    if segment:
        views["segment"] = segment
    ranked = sorted(by_customer.items(), key=lambda item: (-item[1], item[0]))
    concentration = []
    running = 0.0
    for count, (customer_id, amount) in enumerate(ranked, start=1):
        running += amount
        for size, label in _CONCENTRATION:
            if count == size:
                concentration.append({"label": label, "amount": _cents(running)})
    if concentration:
        views["concentration"] = concentration
    if not views:
        return None
    return {"total": _cents(total), "views": views}


def build_revenue_mix_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of_period: str,
) -> dict[str, Any] | None:
    """Close-month revenue by industry, segment, and customer concentration, when it ties to the books."""
    if not table_exists(db, "actual_revenue_recognition") or not table_exists(db, "actual_customers") or not table_exists(db, "gl_actuals"):
        return None
    org = str(organization_id)
    period = str(as_of_period)[:7]
    gl_rows = db.execute(
        text(
            "select period, amount, statement, statement_category, category, account_group, account_name, department "
            "from gl_actuals where cast(organization_id as text) = :org and version = 'Actual' "
            "and left(cast(period as text), 7) = :period"
        ),
        {"org": org, "period": period},
    ).mappings()
    from app.services.reporting.gl_income_statement import build_income_statement_rows

    gl_total = build_income_statement_rows(gl_rows).get(period, {}).get("revenue")
    recognition = db.execute(
        text(
            "select customer_id, sum(cast(recognized_revenue as numeric)) as amount "
            "from actual_revenue_recognition where cast(organization_id as text) = :org "
            "and left(cast(period as text), 7) = :period group by customer_id"
        ),
        {"org": org, "period": period},
    ).mappings()
    by_customer = {
        str(row["customer_id"]): float(row["amount"] or 0)
        for row in recognition
        if row.get("customer_id") and row.get("amount") not in (None, "")
    }
    customers = db.execute(
        text(
            "select customer_id, industry, segment from actual_customers "
            "where cast(organization_id as text) = :org"
        ),
        {"org": org},
    ).mappings()
    attributes = {
        str(row["customer_id"]): (row.get("industry"), row.get("segment"))
        for row in customers
        if row.get("customer_id")
    }
    mix = revenue_mix_views(by_customer, attributes, gl_total)
    if mix is None:
        return None
    mix["period"] = period
    return mix


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
    gtm_months = build_gtm_months(
        db,
        organization_id,
        start_period=start_period,
        as_of_period=as_of_period,
        end_period=end_period,
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
        "GTM_MONTHS": gtm_months,
        "SD": sd,
        "WORKFORCE": workforce,
        "VENDOR_USAGE": build_vendor_usage_payload(db, organization_id),
        "REVENUE_MIX": build_revenue_mix_payload(db, organization_id, as_of_period=as_of_period),
    }
