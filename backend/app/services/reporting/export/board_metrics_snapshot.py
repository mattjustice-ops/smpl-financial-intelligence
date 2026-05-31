"""Extract operational metrics snapshot from a reporting bundle for commentary."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.schemas import ReportingBundle


@dataclass
class BoardMetricsSnapshot:
    as_of: str
    currency: str
    ending_arr: Decimal = Decimal("0")
    net_new_arr: Decimal = Decimal("0")
    new_arr_actual: Decimal = Decimal("0")
    new_arr_budget: Decimal = Decimal("0")
    expansion: Decimal = Decimal("0")
    churn: Decimal = Decimal("0")
    grr: Decimal | None = None
    nrr: Decimal | None = None
    revenue_actual: Decimal = Decimal("0")
    revenue_budget: Decimal = Decimal("0")
    ebitda_actual: Decimal = Decimal("0")
    ebitda_budget: Decimal = Decimal("0")
    cash_actual: Decimal = Decimal("0")
    cash_forecast: Decimal = Decimal("0")
    pipeline_created: Decimal = Decimal("0")
    closed_won: Decimal = Decimal("0")
    closed_lost: Decimal = Decimal("0")
    slipped: Decimal = Decimal("0")
    active_pipeline_proxy: Decimal = Decimal("0")
    marketing_spend: Decimal = Decimal("0")
    pipeline_from_marketing: Decimal = Decimal("0")
    mql: Decimal = Decimal("0")
    sql: Decimal = Decimal("0")
    closed_won_arr_mkt: Decimal = Decimal("0")
    headcount: int = 0
    movement_counts: dict[str, int] = field(default_factory=dict)


def build_metrics_snapshot(bundle: ReportingBundle) -> BoardMetricsSnapshot:
    as_of = bundle.as_of_period
    snap = BoardMetricsSnapshot(as_of=as_of, currency=bundle.currency)

    snap.ending_arr = _wf(bundle, "arr", "ending_arr", as_of) or _wf(bundle, "arr", "ending", as_of)
    snap.net_new_arr = _wf(bundle, "arr", "new_arr", as_of) or _wf(bundle, "arr", "new_business", as_of)
    snap.new_arr_actual = snap.net_new_arr
    snap.new_arr_budget = _wf(bundle, "arr", "new_arr", as_of, "Budget") or _wf(
        bundle, "arr", "new_business", as_of, "Budget"
    )
    snap.expansion = _wf(bundle, "arr", "expansion_arr", as_of) or _wf(bundle, "arr", "expansion", as_of)
    snap.churn = abs(_wf(bundle, "arr", "churn_arr", as_of) or _wf(bundle, "arr", "churn", as_of))
    if snap.ending_arr:
        snap.grr = (snap.ending_arr - snap.churn) / snap.ending_arr

    snap.pipeline_created = _wf(bundle, "pipeline", "pipeline_created", as_of)
    snap.closed_won = abs(_wf(bundle, "pipeline", "closed_won", as_of))
    snap.closed_lost = abs(_wf(bundle, "pipeline", "closed_lost", as_of))
    snap.slipped = abs(_wf(bundle, "pipeline", "slipped_pipeline", as_of))
    snap.active_pipeline_proxy = snap.pipeline_created + snap.slipped

    snap.cash_actual = _wf(bundle, "cash_flow", "ending_cash", as_of, "Actual")
    snap.cash_forecast = _wf(bundle, "cash_flow", "ending_cash", as_of, "Forecast")

    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            p = str(row.period)[:7]
            if p != as_of:
                continue
            if "revenue" in row.line_item.lower() and "deferred" not in row.line_item.lower():
                if row.scenario == "Actual":
                    snap.revenue_actual = row.amount
                elif row.scenario == "Budget":
                    snap.revenue_budget = row.amount
            if "ebitda" in row.line_item.lower():
                if row.scenario == "Actual":
                    snap.ebitda_actual = row.amount
                elif row.scenario == "Budget":
                    snap.ebitda_budget = row.amount

    if bundle.marketing_comparison:
        for row in bundle.marketing_comparison.actual:
            if row.period != as_of:
                continue
            snap.marketing_spend += row.marketing_spend
            snap.pipeline_from_marketing += row.pipeline_arr_created
            snap.mql += row.mqls
            snap.sql += row.sqls
            snap.closed_won_arr_mkt += row.closed_won_arr

    for movement, payload in bundle.pipeline_drilldown.items():
        opps = payload.get("opportunities") or []
        snap.movement_counts[movement] = len(opps)

    snap.headcount = sum(
        int(r.headcount or 0) for r in bundle.headcount if r.period == as_of and r.scenario == "Actual"
    )
    return snap
