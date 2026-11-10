"""Turn a reporting bundle into the named-slot deck's input.

Only lines the close already computed are passed through. A missing close-month
statement returns None so the export can fall back. Go-to-market, customers,
hiring, last year, and the rest-of-year outlook are included when those rows
are loaded. A missing row is left off the deck.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.is_line_resolver import line_item_matches
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import period_range, to_period

REQUIRED = ("revenue", "cogs", "gross_profit", "sm", "rd", "ga", "ebitda", "net_income")

_PLAN_SCENARIOS = ("Budget", "Plan")


def review_input(bundle: ReportingBundle, *, finalized: bool = False, ts_data: dict | None = None) -> dict | None:
    """Input dict for the filler, or None when the close month has no full P&L."""
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs is None:
        return None
    close = to_period(bundle.as_of_period)
    actual = _statement(fs, "Actual", close)
    if actual is None:
        return None
    ytd_list = ytd_periods(close)
    ytd_actual = _sum_statements(fs, "Actual", ytd_list)
    if ytd_actual is None:
        return None

    plan_name = _plan_scenario(fs)
    month_plan = _statement(fs, plan_name, close) if plan_name else None
    ytd_plan = _sum_statements(fs, plan_name, ytd_list) if plan_name else None

    ly_month = _year_ago(close)
    ly = _statement(fs, "Actual", ly_month)
    ly_ytd = _sum_statements(fs, "Actual", [_year_ago(p) for p in ytd_list])

    month: dict = {"actual": actual}
    if month_plan is not None:
        month["plan"] = month_plan
    if ly is not None:
        month["last_year"] = ly
    ytd: dict = {"actual": ytd_actual}
    if ytd_plan is not None:
        ytd["plan"] = ytd_plan
    if ly_ytd is not None:
        ytd["last_year"] = ly_ytd
    pnl: dict = {"month": month, "ytd": ytd}

    q_list = qtd_periods(close)
    q_actual = _sum_statements(fs, "Actual", q_list)
    q_prior = _sum_statements(fs, "Actual", [_prior_quarter_month(p) for p in q_list])
    if q_actual is not None and q_prior is not None:
        pnl["quarter"] = {"actual": q_actual, "prior": q_prior}

    payload: dict = {
        "close": f"{close}-01",
        "fiscal_year_start_month": 1,
        "company": (bundle.organization_name or "Company").strip() or "Company",
        "status": "approved" if finalized else "draft",
        "plan_label": "budget",
        "pnl": pnl,
    }
    arr = _arr(bundle, close, plan_name)
    if arr is not None:
        ly_arr = _arr_side(bundle, _year_ago(close), "Actual")
        if ly_arr is not None:
            arr["last_year_ending"] = ly_arr["ending"]
        payload["arr"] = arr
    cash = _cash(bundle, close, plan_name)
    if cash is not None:
        ly_cash = _cash_side(bundle, _year_ago(close), "Actual")
        if ly_cash is not None:
            cash["last_year_ending"] = ly_cash["ending"]
        payload["cash"] = cash
    gtm, pipe = _gtm_and_pipe(bundle, close, plan_name)
    if gtm is not None:
        payload["gtm"] = gtm
    if pipe is not None:
        payload["pipeline"] = pipe
    history = _history(bundle, close, plan_name)
    if history:
        payload["history"] = history
    customers = _customers(bundle, close)
    if customers:
        payload["customers"] = customers
    people = _people(bundle, close, plan_name)
    if people is not None:
        payload["people"] = people
    cf = _cf_ytd(bundle, ts_data)
    if cf is not None:
        payload["cf_ytd"] = cf
    outlook = _outlook(bundle, fs, close, plan_name, ytd_actual)
    if outlook is not None:
        payload["outlook"] = outlook
    return payload


def _year_ago(period: str) -> str:
    p = to_period(period)
    return f"{int(p[:4]) - 1}-{p[5:7]}"


def _prior_quarter_month(period: str) -> str:
    p = to_period(period)
    month = int(p[5:7]) - 3
    year = int(p[:4])
    if month < 1:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}"


def _plan_scenario(fs) -> str | None:
    seen = {row.scenario for row in fs.income_statement.rows}
    for name in _PLAN_SCENARIOS:
        if name in seen:
            return name
    return None


def _field_of(line_item: str) -> str | None:
    li = line_item.lower().strip()
    if "deferred" in li or "margin" in li:
        return None
    if "sales and marketing" in li or "sales & marketing" in li or li in ("s&m", "sm"):
        return "sm"
    if "research and development" in li or "research & development" in li or li in ("r&d", "rd"):
        return "rd"
    if "general and administrative" in li or "general & administrative" in li or li in ("g&a", "ga"):
        return "ga"
    if line_item_matches("cogs", li):
        return "cogs"
    if line_item_matches("gross profit", li):
        return "gross_profit"
    if line_item_matches("ebitda", li):
        return "ebitda"
    if line_item_matches("net income", li):
        return "net_income"
    if line_item_matches("revenue", li):
        return "revenue"
    return None


def _statement(fs, scenario: str | None, period: str) -> dict[str, float] | None:
    if not scenario:
        return None
    want = to_period(period)
    found: dict[str, Decimal] = {}
    revenue_parts = Decimal("0")
    saw_revenue_part = False
    for row in fs.income_statement.rows:
        if row.scenario != scenario or to_period(str(row.period)[:7]) != want:
            continue
        field = _field_of(row.line_item)
        if field is None:
            continue
        if field == "revenue" and row.line_item.lower().strip() not in ("revenue", "total revenue", "gaap revenue", "total gaap revenue"):
            revenue_parts += row.amount
            saw_revenue_part = True
            continue
        found[field] = row.amount
    if "revenue" not in found and saw_revenue_part and revenue_parts:
        found["revenue"] = revenue_parts
    if "gross_profit" not in found and "revenue" in found and "cogs" in found:
        found["gross_profit"] = found["revenue"] - found["cogs"]
    if any(name not in found for name in REQUIRED):
        return None
    return {name: float(found[name]) for name in REQUIRED}


def _sum_statements(fs, scenario: str | None, periods: list[str]) -> dict[str, float] | None:
    parts = [_statement(fs, scenario, period) for period in periods]
    if not parts or any(part is None for part in parts):
        return None
    return {name: sum(part[name] for part in parts) for name in REQUIRED}


def _wf_amount(bundle: ReportingBundle, key: str, wtype: str, period: str, scenario: str) -> Decimal | None:
    want = to_period(period)
    for row in bundle.comparison_waterfalls.get(key) or []:
        if row.waterfall_type == wtype and row.scenario == scenario and to_period(str(row.period)[:7]) == want:
            return row.amount
    if scenario != "Actual":
        return None
    wf = bundle.executive_flow.waterfalls.get(key)
    if not wf:
        return None
    for row in wf.rows:
        if row.waterfall_type == wtype and to_period(str(row.period)[:7]) == want:
            return row.amount
    return None


def _first_amount(bundle: ReportingBundle, key: str, period: str, scenario: str, *types: str) -> Decimal | None:
    for wtype in types:
        amount = _wf_amount(bundle, key, wtype, period, scenario)
        if amount is not None:
            return amount
    return None


def _arr_side(bundle: ReportingBundle, period: str, scenario: str) -> dict[str, float] | None:
    beginning = _first_amount(bundle, "arr", period, scenario, "beginning_arr", "beginning")
    if beginning is None:
        return None

    def loss(*types: str) -> Decimal:
        amount = _first_amount(bundle, "arr", period, scenario, *types)
        return -abs(amount) if amount is not None else Decimal("0")

    def gain(*types: str) -> Decimal:
        amount = _first_amount(bundle, "arr", period, scenario, *types)
        return amount if amount is not None else Decimal("0")

    new_business = gain("new_business", "new_arr")
    expansion = gain("expansion_arr", "expansion")
    reactivation = gain("reactivation_arr", "reactivation")
    contraction = loss("contraction_arr", "contraction")
    churn = loss("churn_arr", "churn")
    ending = _first_amount(bundle, "arr", period, scenario, "ending_arr", "ending")
    if ending is None:
        ending = beginning + new_business + expansion + reactivation + contraction + churn
    return {
        "beginning": float(beginning),
        "new_business": float(new_business),
        "expansion": float(expansion),
        "reactivation": float(reactivation),
        "contraction": float(contraction),
        "churn": float(churn),
        "ending": float(ending),
    }


def _arr(bundle: ReportingBundle, period: str, plan_name: str | None) -> dict | None:
    actual = _arr_side(bundle, period, "Actual")
    if actual is None:
        return None
    out: dict = {"actual": actual}
    if plan_name:
        plan = _arr_side(bundle, period, plan_name)
        if plan is not None:
            out["plan"] = plan
    return out


def _cash_side(bundle: ReportingBundle, period: str, scenario: str) -> dict[str, float] | None:
    beginning = _first_amount(bundle, "cash_flow", period, scenario, "beginning_cash", "beginning")
    ending = _first_amount(bundle, "cash_flow", period, scenario, "ending_cash", "ending")
    if beginning is None or ending is None:
        return None

    def flow(*types: str, outflow: bool) -> float:
        amount = _first_amount(bundle, "cash_flow", period, scenario, *types)
        if amount is None:
            return 0.0
        return float(-abs(amount) if outflow else amount)

    return {
        "beginning": float(beginning),
        "collections": flow("cash_collections", "collections", outflow=False),
        "payroll": flow("payroll_cash_out", "payroll", outflow=True),
        "vendors": flow("vendor_cash_out", "vendor_payments", "vendor", outflow=True),
        "commissions": flow("commission_cash_out", "commissions", "commission", outflow=True),
        "capex": flow("capex", outflow=True),
        "ending": float(ending),
    }


def _cash(bundle: ReportingBundle, period: str, plan_name: str | None) -> dict | None:
    actual = _cash_side(bundle, period, "Actual")
    if actual is None:
        return None
    out: dict = {"actual": actual}
    if plan_name:
        plan = _cash_side(bundle, period, plan_name)
        if plan is not None:
            out["plan"] = plan
    return out


def _rows_for(block, side: str, period: str) -> list:
    rows = getattr(block, side, None) or []
    want = to_period(period)
    return [row for row in rows if to_period(str(row.period)[:7]) == want]


def _channel_rows(rows: list) -> list:
    out = []
    for row in rows:
        kind = getattr(row, "row_kind", "channel")
        name = str(getattr(row, "marketing_channel", "") or "")
        if kind == "gl_account" or name.startswith("GL:"):
            continue
        if kind not in ("channel", "") or not name:
            continue
        out.append(row)
    return out


def _total_row(rows: list):
    totals = [row for row in rows if getattr(row, "row_kind", "") == "total"]
    if totals:
        return totals[0]
    channels = _channel_rows(rows)
    if not channels:
        return None
    return channels[0] if len(channels) == 1 else _sum_marketing(channels)


def _sum_marketing(rows: list):
    first = rows[0]

    class _Total:
        pass

    total = _Total()
    total.mqls = sum((row.mqls for row in rows), Decimal("0"))
    total.sqls = sum((row.sqls for row in rows), Decimal("0"))
    total.sals = sum((row.sals for row in rows), Decimal("0"))
    total.opportunities_created = sum((row.opportunities_created for row in rows), Decimal("0"))
    total.marketing_spend = sum((row.marketing_spend for row in rows), Decimal("0"))
    total.pipeline_arr_created = sum((row.pipeline_arr_created for row in rows), Decimal("0"))
    total.closed_won_arr = sum((row.closed_won_arr for row in rows), Decimal("0"))
    total.closed_lost_arr = sum((row.closed_lost_arr for row in rows), Decimal("0"))
    total.slipped_pipeline_arr = sum((row.slipped_pipeline_arr for row in rows), Decimal("0"))
    total.beginning_pipeline_arr = sum((row.beginning_pipeline_arr for row in rows), Decimal("0"))
    total.ending_pipeline_arr = sum((row.ending_pipeline_arr for row in rows), Decimal("0"))
    total.organization_id = first.organization_id
    return total


def _funnel(row) -> dict[str, float]:
    return {
        "mql": float(row.mqls or 0),
        "sql": float(row.sqls or 0),
        "sal": float(row.sals or 0),
        "opp": float(row.opportunities_created or 0),
    }


def _gtm_and_pipe(bundle: ReportingBundle, period: str, plan_name: str | None = None) -> tuple[dict | None, dict | None]:
    channels_block = bundle.marketing_channel_comparison
    totals_block = bundle.marketing_comparison or channels_block
    if totals_block is None and channels_block is None:
        return None, _pipe(bundle, period, plan_name)
    actual_totals = _rows_for(totals_block, "actual", period) if totals_block is not None else []
    budget_totals = _rows_for(totals_block, "budget", period) if totals_block is not None else []
    actual_total = _total_row(actual_totals)
    budget_total = _total_row(budget_totals)
    channel_source = channels_block or totals_block
    actual_channels = _channel_rows(_rows_for(channel_source, "actual", period)) if channel_source is not None else []
    budget_channels = _channel_rows(_rows_for(channel_source, "budget", period)) if channel_source is not None else []
    budget_by_name = {str(row.marketing_channel): row for row in budget_channels}

    source_rows = _rows_for(channel_source, "actual", period) if channel_source is not None else []
    gtm = None
    if actual_total is not None or actual_channels or _gl_rows(source_rows):
        channels = _spend_channels(channel_source, period, actual_channels, budget_by_name)
        funnel_actual = _funnel(actual_total) if actual_total is not None else {"mql": 0, "sql": 0, "sal": 0, "opp": 0}
        gtm = {"channels": channels, "funnel": {"actual": funnel_actual}}
        if budget_total is not None:
            gtm["funnel"]["plan"] = {
                "mql": float(budget_total.mqls or 0),
                "sql": float(budget_total.sqls or 0),
                "sal": float(budget_total.sals or 0),
                "opp": float(budget_total.opportunities_created or 0),
            }

    pipe = _pipe(bundle, period, plan_name)
    if pipe is None and actual_total is not None and any(
        getattr(actual_total, name, 0)
        for name in ("beginning_pipeline_arr", "pipeline_arr_created", "ending_pipeline_arr")
    ):
        pipe = {"actual": _marketing_pipe(actual_total)}
        if budget_total is not None:
            pipe["plan"] = _marketing_pipe(budget_total)
    return gtm, pipe


def _gl_rows(rows: list) -> list:
    out = []
    for row in rows:
        kind = getattr(row, "row_kind", "")
        name = str(getattr(row, "marketing_channel", "") or "")
        if kind == "gl_account" or name.startswith("GL:"):
            out.append(row)
    return out


def _spend_channels(channel_source, period: str, actual_channels: list, budget_by_name: dict) -> list[dict]:
    """Spend is on the GL program accounts. Channel rows carry volume, not the spend."""
    gl_actual = _gl_rows(_rows_for(channel_source, "actual", period)) if channel_source is not None else []
    gl_budget = _gl_rows(_rows_for(channel_source, "budget", period)) if channel_source is not None else []
    if gl_actual or gl_budget:
        budget_gl = {str(row.marketing_channel): row for row in gl_budget}
        names = []
        seen = set()
        for row in gl_actual + gl_budget:
            name = str(row.marketing_channel)
            if name not in seen:
                seen.add(name)
                names.append(name)
        channels = []
        for name in names:
            actual = next((row for row in gl_actual if str(row.marketing_channel) == name), None)
            plan_row = budget_gl.get(name)
            label = name[3:].strip() if name.startswith("GL:") else name
            item = {"name": label or name, "spend": float(actual.marketing_spend or 0) if actual is not None else 0.0}
            if plan_row is not None:
                item["plan"] = float(plan_row.marketing_spend or 0)
            channels.append(item)
        return channels
    channels = []
    for row in actual_channels:
        name = str(row.marketing_channel)
        plan_row = budget_by_name.get(name)
        item = {"name": name, "spend": float(row.marketing_spend or 0)}
        if plan_row is not None:
            item["plan"] = float(plan_row.marketing_spend or 0)
        channels.append(item)
    return channels


def _marketing_pipe(row) -> dict[str, float]:
    return {
        "beginning": float(row.beginning_pipeline_arr or 0),
        "created": float(row.pipeline_arr_created or 0),
        "closed_won": -abs(float(row.closed_won_arr or 0)),
        "closed_lost": -abs(float(row.closed_lost_arr or 0)),
        "slipped": -abs(float(row.slipped_pipeline_arr or 0)),
        "ending": float(row.ending_pipeline_arr or 0),
    }


def _pipe_side(bundle: ReportingBundle, period: str, scenario: str) -> dict[str, float] | None:
    """Pipeline bridge from the pipeline waterfall. Decreases keep the stored sign."""
    beginning = _first_amount(bundle, "pipeline", period, scenario, "beginning_pipeline")
    created = _first_amount(bundle, "pipeline", period, scenario, "pipeline_created")
    won = _first_amount(bundle, "pipeline", period, scenario, "closed_won")
    lost = _first_amount(bundle, "pipeline", period, scenario, "closed_lost")
    slipped = _first_amount(bundle, "pipeline", period, scenario, "slipped_pipeline")
    ending = _first_amount(bundle, "pipeline", period, scenario, "ending_pipeline")
    if all(amount is None for amount in (beginning, created, won, lost, slipped, ending)):
        return None

    def num(amount) -> float:
        return float(amount) if amount is not None else 0.0

    start = num(beginning)
    flows = num(created) + num(won) + num(lost) + num(slipped)
    close = num(ending) if ending is not None else start + flows
    return {
        "beginning": start,
        "created": num(created),
        "closed_won": num(won),
        "closed_lost": num(lost),
        "slipped": num(slipped),
        "ending": close,
    }


def _pipe(bundle: ReportingBundle, period: str, plan_name: str | None) -> dict | None:
    actual = _pipe_side(bundle, period, "Actual")
    if actual is None:
        return None
    out: dict = {"actual": actual}
    if plan_name:
        plan = _pipe_side(bundle, period, plan_name)
        if plan is not None:
            out["plan"] = plan
    return out


def _history(bundle: ReportingBundle, close: str, plan_name: str | None) -> list[dict]:
    rows = []
    for period in ytd_periods(close):
        if period == to_period(close):
            continue
        entry: dict = {"month": period}
        arr = _arr(bundle, period, plan_name)
        if arr is not None:
            entry["arr"] = arr
        gtm, pipe = _gtm_and_pipe(bundle, period, plan_name)
        if gtm is not None:
            entry["gtm"] = gtm
        if pipe is not None:
            entry["pipeline"] = pipe
        if len(entry) > 1:
            rows.append(entry)
    return rows


_CUSTOMER_PARTS = {"new_logo", "winback", "first_year_expansion"}
_CUSTOMER_BUCKET = {
    "new_business": "new_business",
    "new_arr": "new_business",
    "new_logo": "new_business",
    "winback": "new_business",
    "first_year_expansion": "new_business",
    "expansion": "expansion",
    "expansion_arr": "expansion",
    "reactivation": "expansion",
    "reactivation_arr": "expansion",
    "contraction": "contraction",
    "contraction_arr": "contraction",
    "first_year_contraction": "contraction",
    "no_start": "contraction",
    "churn": "churn",
    "churn_arr": "churn",
}


def _customer_name(row) -> str:
    name = (getattr(row, "customer_name", None) or "").strip()
    if name:
        return name
    raw = getattr(row, "raw", None) or {}
    if not isinstance(raw, dict):
        return ""
    for key in ("customer_name", "customer", "account_name", "account", "name"):
        value = raw.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _named_amount(opp) -> tuple[str, float]:
    if not isinstance(opp, dict):
        name = _customer_name(opp)
        amount = getattr(opp, "arr_impact", None)
        if amount in (None, 0):
            amount = getattr(opp, "amount", 0)
    else:
        name = str(opp.get("customer_name") or opp.get("opportunity_name") or "").strip()
        amount = opp.get("arr_impact")
        if amount in (None, 0):
            amount = opp.get("amount") or 0
    return name, abs(float(amount or 0))


def _customers(bundle: ReportingBundle, close: str) -> dict:
    want = to_period(close)
    grouped: dict[tuple[str, str], float] = {}
    part_customers: set[str] = set()
    rollup: dict[str, float] = {}
    for row in getattr(bundle, "arr_customers", None) or []:
        if to_period(str(row.period)[:7]) != want or row.scenario not in ("Actual", "actual"):
            continue
        name = _customer_name(row)
        if not name:
            continue
        kind = row.waterfall_type
        if kind in _CUSTOMER_PARTS:
            part_customers.add(name)
        bucket = _CUSTOMER_BUCKET.get(kind)
        if bucket is None:
            continue
        amount = float(row.arr_impact or 0)
        if amount == 0:
            continue
        if kind in ("new_business", "new_arr"):
            rollup[name] = rollup.get(name, 0.0) + amount
            continue
        key = (bucket, name)
        grouped[key] = grouped.get(key, 0.0) + amount
    for name, amount in rollup.items():
        if name in part_customers or amount == 0:
            continue
        key = ("new_business", name)
        grouped[key] = grouped.get(key, 0.0) + amount
    out: dict[str, list[dict]] = {}
    for (bucket, name), amount in grouped.items():
        out.setdefault(bucket, []).append({"name": name, "arr": amount})

    named = {name for rows in out.values() for name in (row["name"] for row in rows)}
    drill = bundle.pipeline_drilldown or {}
    for key, bucket in (("closed_won", "closed_won"), ("slipped_pipeline", "slipped")):
        for opp in ((drill.get(key) or {}).get("opportunities") or []):
            name, amount = _named_amount(opp)
            if not name or not amount or name in named:
                continue
            named.add(name)
            out.setdefault(bucket, []).append({"name": name, "arr": amount})
    return {key: value for key, value in out.items() if value}


def _year_months(close: str) -> list[str]:
    year = int(to_period(close)[:4])
    return period_range(f"{year:04d}-01", f"{year:04d}-12")


def _open_months(close: str) -> list[str]:
    current = to_period(close)
    return [period for period in _year_months(close) if period > current]


def _bs_cash(fs, scenario: str, period: str) -> float | None:
    want = to_period(period)
    for row in fs.balance_sheet.rows:
        if row.scenario != scenario or to_period(str(row.period)[:7]) != want:
            continue
        label = row.line_item.lower()
        if label == "cash" or "cash and cash equivalents" in label:
            return float(row.amount)
    return None


def _ending_arr(bundle: ReportingBundle, period: str, scenario: str) -> float | None:
    amount = _first_amount(bundle, "arr", period, scenario, "ending_arr", "ending")
    return None if amount is None else float(amount)


def _outlook(bundle: ReportingBundle, fs, close: str, plan_name: str | None, ytd_actual: dict) -> dict | None:
    open_months = _open_months(close)
    december = _year_months(close)[-1]
    if open_months:
        rest = _sum_statements(fs, "Forecast", open_months)
        if rest is None:
            return None
        revenue = ytd_actual["revenue"] + rest["revenue"]
        ebitda = ytd_actual["ebitda"] + rest["ebitda"]
        gross_profit = ytd_actual["gross_profit"] + rest["gross_profit"]
        rest_margin = (rest["gross_profit"] / rest["revenue"]) if rest["revenue"] else None
    else:
        revenue = ytd_actual["revenue"]
        ebitda = ytd_actual["ebitda"]
        gross_profit = ytd_actual["gross_profit"]
        rest_margin = None
    if not revenue:
        return None
    ending_arr = _ending_arr(bundle, december, "Forecast")
    ending_cash = _bs_cash(fs, "Forecast", december)
    if ending_cash is None:
        amount = _first_amount(bundle, "cash_flow", december, "Forecast", "ending_cash", "ending")
        ending_cash = None if amount is None else float(amount)
    if ending_arr is None or ending_cash is None:
        return None
    fy = {
        "ending_arr": ending_arr,
        "revenue": revenue,
        "gross_margin": gross_profit / revenue,
        "ebitda": ebitda,
        "ending_cash": ending_cash,
    }
    outlook: dict = {"fy": fy}
    if rest_margin is not None:
        outlook["rest_of_year_gross_margin"] = rest_margin
    if plan_name:
        plan_year = _sum_statements(fs, plan_name, _year_months(close))
        plan_arr = _ending_arr(bundle, december, plan_name)
        plan_cash = _bs_cash(fs, plan_name, december)
        if plan_cash is None:
            amount = _first_amount(bundle, "cash_flow", december, plan_name, "ending_cash", "ending")
            plan_cash = None if amount is None else float(amount)
        if plan_year is not None and plan_year["revenue"] and plan_arr is not None and plan_cash is not None:
            outlook["plan_fy"] = {
                "ending_arr": plan_arr,
                "revenue": plan_year["revenue"],
                "gross_margin": plan_year["gross_profit"] / plan_year["revenue"],
                "ebitda": plan_year["ebitda"],
                "ending_cash": plan_cash,
            }
    return outlook


def _labor(row) -> dict[str, float] | None:
    fields = ("salaries", "taxes_benefits", "variable_pay", "stock_comp")
    if row is None or all(getattr(row, name, None) is None for name in fields):
        return None
    return {
        "salaries": float(row.salaries or 0),
        "taxes_benefits": float(row.taxes_benefits or 0),
        "variable": float(row.variable_pay or 0),
        "sbc": float(row.stock_comp or 0),
    }


def _people(bundle: ReportingBundle, close: str, plan_name: str | None) -> dict | None:
    """Department hiring and pay mix from the workforce rows already on the bundle."""
    want = to_period(close)
    rows = [
        row for row in (bundle.headcount or [])
        if to_period(str(row.period)[:7]) == want and row.scenario == "Actual" and row.department
    ]
    if not rows:
        return None
    plan_rows = {
        row.department: row
        for row in (bundle.headcount or [])
        if plan_name and to_period(str(row.period)[:7]) == want and row.scenario == plan_name and row.department
    }
    departments = []
    for row in rows:
        plan = plan_rows.get(row.department)
        close_heads = float(row.headcount or 0)
        hires = float(row.hires) if row.hires is not None else None
        departures = float(row.departures) if row.departures is not None else None
        if row.heads_open is not None:
            opening = float(row.heads_open)
        elif hires is not None or departures is not None:
            opening = close_heads - (hires or 0) + (departures or 0)
        else:
            opening = close_heads
        labor = {"actual": _labor(row)} if _labor(row) else {}
        plan_labor = _labor(plan)
        if plan_labor is not None:
            labor["plan"] = plan_labor
        departments.append({
            "name": row.department,
            "heads_open": opening,
            "hires": hires or 0,
            "departures": departures or 0,
            "heads_close": close_heads,
            "heads_plan": None if plan is None or plan.headcount is None else float(plan.headcount),
            "labor": labor,
        })
    if not any(item["heads_close"] or item["heads_open"] or item["hires"] or item["departures"] for item in departments):
        return None
    year_end = f"{want[:4]}-12"

    def total(scenario: str | None) -> float | None:
        if not scenario:
            return None
        matched = [
            row for row in (bundle.headcount or [])
            if to_period(str(row.period)[:7]) == year_end and row.scenario == scenario
        ]
        if not matched:
            return None
        return float(sum((row.headcount or 0) for row in matched))

    ye = {}
    plan_ye = total(plan_name)
    outlook_ye = total("Forecast")
    if plan_ye is not None:
        ye["plan"] = plan_ye
    if outlook_ye is not None:
        ye["outlook"] = outlook_ye
    return {"departments": departments, "year_end": ye}


_CF_KEYS = {
    "beginning": "beginning_cash",
    "net_income": "net_income",
    "da": "da",
    "sbc": "sbc",
    "ar": "chg_ar",
    "deferred_revenue": "chg_dr",
    "ap": "chg_ap",
    "prepaids": "chg_prepaids",
    "deferred_commissions": "chg_deferred_commissions",
    "cfo": "cfo",
    "capex": "capex",
    "cff": "cff",
    "net_change": "net_change",
    "ending": "ending_cash",
}


def _cf_side(raw: dict | None) -> dict[str, float] | None:
    if not raw or not any(value not in (None, 0, 0.0) for value in raw.values()):
        return None
    return {name: float(raw.get(source) or 0) for name, source in _CF_KEYS.items()}


def _cf_ytd(bundle: ReportingBundle, ts_data: dict | None) -> dict | None:
    from app.services.reporting.export.board_platform_metrics import build_ytd_cash_flow_statement

    block = build_ytd_cash_flow_statement(bundle, ts_data)
    actual = _cf_side((block.get("actual") or {}).get("raw"))
    if actual is None:
        return None
    out = {"actual": actual}
    plan = _cf_side((block.get("budget") or {}).get("raw"))
    if plan is not None:
        out["plan"] = plan
    return out


def attach_prior_year(db, organization_id, bundle: ReportingBundle) -> None:
    """Add last year's statements and ARR and cash bridges so the deck can compare them.

    The export window is the close year. June 2025 and the first half sit before that
    window, so they are loaded here and appended. A missing prior year leaves the
    comparison blank.
    """
    import uuid

    from app.services.reporting.export.multi_scenario import (
        collect_comparison_financial_statements,
        collect_comparison_waterfalls,
    )

    close = to_period(bundle.as_of_period)
    year = int(close[:4]) - 1
    start = f"{year:04d}-01"
    end = f"{year:04d}-{close[5:7]}"
    org = organization_id if isinstance(organization_id, uuid.UUID) else uuid.UUID(str(organization_id))
    try:
        extra = collect_comparison_financial_statements(db, org, start_period=start, end_period=end)
    except Exception:
        extra = None
    target = bundle.comparison_financial_statements or bundle.financial_statements
    if extra is not None and target is not None:
        target.income_statement.rows.extend(extra.income_statement.rows)
        target.balance_sheet.rows.extend(extra.balance_sheet.rows)
        target.cash_flow.rows.extend(extra.cash_flow.rows)
    try:
        waterfalls = collect_comparison_waterfalls(db, org, start_period=start, end_period=end)
    except Exception:
        waterfalls = {}
    for key in ("arr", "cash_flow"):
        rows = (waterfalls or {}).get(key) or []
        if rows:
            bundle.comparison_waterfalls.setdefault(key, []).extend(rows)
