"""Board tables inspired by reference-decks (CARET / Airship BOD patterns)."""

from __future__ import annotations

from decimal import Decimal

from app.services.board_package.package import fmt_money, fmt_pct
from app.services.board_package.schemas import TableSpec
from app.services.reporting.export.board_chart_service import _wf, channel_efficiency_table
from app.services.reporting.export.board_format_utils import variance_subtext
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.schemas import ReportingBundle


def _pct_var(actual: Decimal, compare: Decimal) -> str:
    if compare == 0:
        return "n/a"
    return f"{float((actual - compare) / compare):.0%}"


def executive_dashboard_table(bundle: ReportingBundle) -> TableSpec:
    """IMG 8039 — Metric | Actual | Budget | vs Plan | Notes."""
    m = build_metrics_snapshot(bundle)
    cur = bundle.currency
    arr_b = _wf(bundle, "arr", "ending_arr", m.as_of, "Budget") or _wf(bundle, "arr", "ending", m.as_of, "Budget")
    rev_b = m.revenue_budget
    ebitda_b = Decimal("0")
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            if str(row.period)[:7] != m.as_of:
                continue
            if row.scenario == "Budget" and "ebitda" in row.line_item.lower():
                ebitda_b = row.amount

    rows: list[list[str]] = [
        [
            "Ending ARR",
            fmt_money(m.ending_arr, cur),
            fmt_money(arr_b, cur),
            _pct_var(m.ending_arr, arr_b),
            variance_subtext(m.ending_arr, arr_b, currency=cur, label="Δ"),
        ],
        [
            "Net New ARR",
            fmt_money(m.net_new_arr, cur),
            fmt_money(m.new_arr_budget, cur),
            _pct_var(m.net_new_arr, m.new_arr_budget),
            "",
        ],
        [
            "Revenue (close month)",
            fmt_money(m.revenue_actual, cur),
            fmt_money(rev_b, cur),
            _pct_var(m.revenue_actual, rev_b),
            "",
        ],
        [
            "EBITDA (close month)",
            fmt_money(m.ebitda_actual, cur),
            fmt_money(ebitda_b, cur),
            _pct_var(m.ebitda_actual, ebitda_b),
            "",
        ],
        [
            "Ending Cash",
            fmt_money(m.cash_actual, cur),
            fmt_money(m.cash_forecast, cur),
            _pct_var(m.cash_actual, m.cash_forecast) if m.cash_forecast else "n/a",
            "Bridge ties to balance sheet",
        ],
        [
            "Pipeline Created",
            fmt_money(m.pipeline_created, cur),
            "—",
            "—",
            "Period activity",
        ],
        [
            "Closed Won ARR",
            fmt_money(m.closed_won, cur),
            "—",
            "—",
            "CRM movement",
        ],
        [
            "Headcount",
            str(m.headcount),
            "—",
            "—",
            "Actual FTE",
        ],
    ]
    return TableSpec(
        headers=["Metric", "Actual", "Budget / Fcst", "vs Plan", "Context"],
        rows=rows,
    )


def bookings_variance_table(bundle: ReportingBundle) -> TableSpec | None:
    """Slide 5 style — key booking / pipeline lines with Actual, Budget, Forecast."""
    as_of = bundle.as_of_period
    cur = bundle.currency
    lines = [
        ("Pipeline Created", "pipeline", "pipeline_created"),
        ("Closed Won", "pipeline", "closed_won"),
        ("Closed Lost", "pipeline", "closed_lost"),
        ("Slipped / Deferred", "pipeline", "slipped_pipeline"),
        ("Net New ARR", "arr", "new_arr"),
        ("Expansion ARR", "arr", "expansion_arr"),
        ("Churn ARR", "arr", "churn_arr"),
    ]
    rows: list[list[str]] = []
    for label, key, wtype in lines:
        actual = _wf(bundle, key, wtype, as_of, "Actual")
        if wtype == "churn_arr" or wtype == "churn":
            actual = abs(actual)
        budget = _wf(bundle, key, wtype, as_of, "Budget")
        forecast = _wf(bundle, key, wtype, as_of, "Forecast")
        if actual == 0 and budget == 0 and forecast == 0:
            continue
        rows.append(
            [
                label,
                fmt_money(actual, cur),
                fmt_money(budget, cur),
                fmt_money(forecast, cur),
                fmt_money(actual - budget, cur) if budget else "—",
            ]
        )
    if not rows:
        return None
    return TableSpec(
        headers=["Driver", "Actual", "Budget", "Forecast", "vs Budget"],
        rows=rows[:10],
    )


def marketing_rollup_table(bundle: ReportingBundle) -> TableSpec | None:
    """Slide 11 — Spend → Funnel → Efficiency for close month vs budget where available."""
    as_of = bundle.as_of_period
    cur = bundle.currency
    mkt = bundle.marketing_comparison
    if not mkt:
        return None

    def _sum(rows, field: str, scen: str) -> Decimal:
        total = Decimal("0")
        for row in rows:
            if row.period != as_of:
                continue
            if scen == "actual":
                total += getattr(row, field, Decimal("0"))
            elif scen == "budget" and hasattr(row, field):
                total += getattr(row, field, Decimal("0"))
        return total

    spend_a = _sum(mkt.actual, "marketing_spend", "actual")
    spend_b = _sum(mkt.budget, "marketing_spend", "budget") if mkt.budget else Decimal("0")
    mql_a = _sum(mkt.actual, "mqls", "actual")
    sql_a = _sum(mkt.actual, "sqls", "actual")
    pipe_a = _sum(mkt.actual, "pipeline_arr_created", "actual")
    won_a = _sum(mkt.actual, "closed_won_arr", "actual")
    ratio_a = (pipe_a / spend_a) if spend_a else Decimal("0")
    ratio_b = (
        (_sum(mkt.budget, "pipeline_arr_created", "budget") / spend_b) if spend_b and mkt.budget else Decimal("0")
    )

    rows = [
        ["Total Marketing Spend", fmt_money(spend_a, cur), fmt_money(spend_b, cur), _pct_var(spend_a, spend_b)],
        ["MQLs Created", f"{int(mql_a)}", "—", "—"],
        ["SQLs Created", f"{int(sql_a)}", "—", "—"],
        ["Pipeline Created (ARR)", fmt_money(pipe_a, cur), "—", "—"],
        ["Bookings Won (ARR)", fmt_money(won_a, cur), "—", "—"],
        ["Pipeline / Spend", f"{float(ratio_a):.1f}x", f"{float(ratio_b):.1f}x" if ratio_b else "—", _pct_var(ratio_a, ratio_b) if ratio_b else "—"],
    ]
    if spend_a and won_a:
        rows.append(["Cost per Win", fmt_money(spend_a / max(won_a / Decimal("1"), Decimal("1")), cur), "—", "—"])

    return TableSpec(headers=["Metric", "Actual", "Budget", "vs Budget"], rows=rows)


def funnel_period_table(bundle: ReportingBundle) -> TableSpec | None:
    """Slide 3/4 simplified — funnel counts + closed won ARR; variance row vs budget when present."""
    as_of = bundle.as_of_period
    cur = bundle.currency
    mkt = bundle.marketing_comparison
    if not mkt:
        return None
    mql = sql = sal = opp = Decimal("0")
    for row in mkt.actual:
        if row.period == as_of:
            mql += row.mqls
            sql += row.sqls
            sal += row.sals
            opp += row.opportunities_created
    won = abs(_wf(bundle, "pipeline", "closed_won", as_of))
    rows = [
        ["MQLs", f"{int(mql)}", "—", "—"],
        ["SQLs", f"{int(sql)}", "—", "—"],
        ["SALs", f"{int(sal)}", "—", "—"],
        ["Opportunities Created", f"{int(opp)}", "—", "—"],
        ["Closed Won ARR", fmt_money(won, cur), "—", "—"],
    ]
    if mql and sql:
        rows.insert(4, ["MQL → SQL %", f"{float(sql / mql):.0%}", "—", "—"])
    return TableSpec(headers=["Stage", "Actual", "Budget", "vs Budget"], rows=rows)


def arr_rollforward_table(bundle: ReportingBundle) -> TableSpec | None:
    """Slide 6 — ARR bridge rows for close month."""
    as_of = bundle.as_of_period
    cur = bundle.currency
    order = [
        ("beginning_arr", "Beginning ARR"),
        ("new_arr", "New Business"),
        ("new_business", "New Business"),
        ("expansion_arr", "Expansion"),
        ("expansion", "Expansion"),
        ("contraction_arr", "Contraction"),
        ("contraction", "Contraction"),
        ("churn_arr", "Churn"),
        ("churn", "Churn"),
        ("ending_arr", "Ending ARR"),
        ("ending", "Ending ARR"),
    ]
    seen: set[str] = set()
    rows: list[list[str]] = []
    for wtype, label in order:
        if label in seen:
            continue
        a = _wf(bundle, "arr", wtype, as_of, "Actual")
        b = _wf(bundle, "arr", wtype, as_of, "Budget")
        if wtype in ("churn_arr", "churn", "contraction_arr", "contraction"):
            a, b = abs(a), abs(b)
        if a == 0 and b == 0 and label not in ("Beginning ARR", "Ending ARR"):
            continue
        seen.add(label)
        rows.append([label, fmt_money(a, cur), fmt_money(b, cur), fmt_money(a - b, cur) if b else "—"])
    if len(rows) < 2:
        return None
    return TableSpec(headers=["ARR Component", "Actual", "Budget", "vs Budget"], rows=rows)
