"""Turn a reporting bundle into the named-slot deck's input.

Only lines the close already computed are passed through. A missing close-month
statement returns None so the export can fall back. Nothing here invents a
customer list, a hiring outlook, or a rest-of-year forecast.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.is_line_resolver import line_item_matches
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

REQUIRED = ("revenue", "cogs", "gross_profit", "sm", "rd", "ga", "ebitda", "net_income")

_PLAN_SCENARIOS = ("Budget", "Plan")


def review_input(bundle: ReportingBundle) -> dict | None:
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
        "status": "draft",
        "plan_label": "budget",
        "pnl": pnl,
    }
    arr = _arr(bundle, close, plan_name)
    if arr is not None:
        payload["arr"] = arr
    cash = _cash(bundle, close, plan_name)
    if cash is not None:
        payload["cash"] = cash
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
