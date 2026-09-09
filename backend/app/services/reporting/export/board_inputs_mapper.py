"""Map live dashboard data to commentary / board package inputs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.commentary.schemas import (
    CashCollectionsForecastInput,
    CommentaryInputs,
    MrrWaterfallSummary,
    PipelineChange,
    RevenueForecastInput,
    VarianceRow,
)
from app.services.dashboard.schemas import (
    ExecutiveFlowResponse,
    WaterfallResponse,
    WaterfallSummaryRow,
)
from app.services.financial_statements.financial_statement_service import SummaryResponse
from app.services.reporting.export.schemas import waterfall_by_type
from app.services.reporting.period_utils import to_period


def _arr_waterfall_for_period(waterfall: WaterfallResponse | None, period: str) -> MrrWaterfallSummary | None:
    if waterfall is None:
        return None
    beginning = waterfall_by_type(waterfall, "beginning_arr", period) or waterfall_by_type(
        waterfall, "beginning_balance", period
    )
    ending = waterfall_by_type(waterfall, "ending_arr", period) or waterfall_by_type(
        waterfall, "ending_balance", period
    )
    if beginning == 0 and ending == 0:
        return None
    return MrrWaterfallSummary(
        period=date(int(period[:4]), int(period[5:7]), 1),
        beginning_mrr=beginning / Decimal("12"),
        new_mrr=waterfall_by_type(waterfall, "new_arr", period) / Decimal("12"),
        expansion_mrr=waterfall_by_type(waterfall, "expansion_arr", period) / Decimal("12"),
        contraction_mrr=waterfall_by_type(waterfall, "contraction_arr", period) / Decimal("12"),
        churn_mrr=waterfall_by_type(waterfall, "churn_arr", period) / Decimal("12"),
        reactivation_mrr=waterfall_by_type(waterfall, "reactivation_arr", period) / Decimal("12"),
        ending_mrr=ending / Decimal("12"),
    )


#: Exact income-statement labels that carry top-line revenue, most specific first.
#: Substring matching is deliberately avoided — "cost of revenue" and "deferred
#: revenue" both contain "revenue" and must never land in a top-line total.
REVENUE_LINE_ITEMS = ("total revenue", "revenue")


def _revenue_input_for_period(
    financial: SummaryResponse | None, period: str
) -> RevenueForecastInput | None:
    """Actual / Budget / Forecast revenue for one period.

    Every scenario is collected before a value is chosen so variance commentary
    sees actual against plan. "Total revenue" wins over "revenue" within a
    scenario so a subtotal and its component are never added together.
    """
    if financial is None:
        return None

    by_scenario: dict[str, dict[str, Decimal]] = {}
    row_period: date | None = None
    for row in financial.income_statement.rows:
        if str(row.period)[:7] != period:
            continue
        line_item = (row.line_item or "").strip().lower()
        if line_item not in REVENUE_LINE_ITEMS:
            continue
        scenario = (row.scenario or "").strip().lower()
        bucket = by_scenario.setdefault(scenario, {})
        bucket[line_item] = bucket.get(line_item, Decimal("0")) + row.amount
        if row_period is None:
            row_period = row.period

    if not by_scenario or row_period is None:
        return None

    def pick(scenario: str) -> Decimal | None:
        bucket = by_scenario.get(scenario)
        if not bucket:
            return None
        for line_item in REVENUE_LINE_ITEMS:
            if line_item in bucket:
                return bucket[line_item]
        return None

    return RevenueForecastInput(
        period_start=row_period,
        period_end=row_period,
        forecasted_revenue=pick("forecast"),
        actual_revenue=pick("actual"),
        budget_revenue=pick("budget"),
    )


#: Warehouse waterfall_type spellings per ARR movement. The comparison waterfalls
#: emit the bare forms ("ending", "new_business"); the "_arr" / "_balance" variants
#: come from older loads and are kept so both shapes resolve.
ARR_MOVEMENT_TYPES: dict[str, tuple[str, ...]] = {
    "beginning": ("beginning", "beginning_arr", "beginning_balance"),
    "ending": ("ending", "ending_arr", "ending_balance"),
    "new": ("new_business", "new_arr"),
    "expansion": ("expansion", "expansion_arr"),
    "contraction": ("contraction", "contraction_arr"),
    "churn": ("churn", "churn_arr"),
    "reactivation": ("reactivation", "reactivation_arr"),
}


def _period_date(period: str) -> date:
    return date(int(period[:4]), int(period[5:7]), 1)


def _comparison_amount(
    rows: list[WaterfallSummaryRow] | None,
    types: tuple[str, ...],
    period: str,
    scenario: str,
) -> Decimal | None:
    """First matching amount from the comparison waterfalls, or None if absent.

    None and zero are kept distinct: a missing row means the model should say the
    input was not provided, while a real zero is a fact it may cite.
    """
    for row in rows or []:
        if row.period != period:
            continue
        if (row.scenario or "").strip().lower() != scenario:
            continue
        if row.waterfall_type in types:
            return row.amount
    return None


def _variance_row(
    metric: str,
    actual: Decimal | None,
    baseline: Decimal | None,
    *,
    higher_is_better: bool = True,
) -> VarianceRow | None:
    if actual is None or baseline is None:
        return None
    delta = actual - baseline
    if delta == 0:
        direction = "neutral"
    elif (delta > 0) == higher_is_better:
        direction = "favorable"
    else:
        direction = "unfavorable"
    return VarianceRow(
        metric=metric,
        actual=actual,
        forecast=baseline,
        variance_absolute=delta,
        variance_percent=(delta / baseline * Decimal("100")) if baseline else None,
        direction=direction,
    )


def _mrr_from_comparison(
    rows: list[WaterfallSummaryRow] | None, period: str
) -> MrrWaterfallSummary | None:
    """MRR summary from the comparison waterfalls when executive flow has none."""

    def amt(movement: str) -> Decimal:
        types = ARR_MOVEMENT_TYPES[movement]
        return _comparison_amount(rows, types, period, "actual") or Decimal("0")

    beginning = amt("beginning")
    ending = amt("ending")
    if beginning == 0 and ending == 0:
        return None
    twelve = Decimal("12")
    return MrrWaterfallSummary(
        period=_period_date(period),
        beginning_mrr=beginning / twelve,
        new_mrr=amt("new") / twelve,
        expansion_mrr=amt("expansion") / twelve,
        contraction_mrr=amt("contraction") / twelve,
        churn_mrr=amt("churn") / twelve,
        reactivation_mrr=amt("reactivation") / twelve,
        ending_mrr=ending / twelve,
    )


def build_commentary_inputs(
    *,
    organization_name: str | None,
    as_of_period: str,
    bundle_data: ExecutiveFlowResponse,
    financial: SummaryResponse | None,
    comparison_waterfalls: dict[str, list[WaterfallSummaryRow]] | None = None,
) -> CommentaryInputs:
    period = to_period(as_of_period)
    arr_rows = (comparison_waterfalls or {}).get("arr")
    pipeline_rows = (comparison_waterfalls or {}).get("pipeline")
    cash_rows = (comparison_waterfalls or {}).get("cash_flow")

    mrr = _arr_waterfall_for_period(bundle_data.waterfalls.get("arr"), period)
    if mrr is None:
        mrr = _mrr_from_comparison(arr_rows, period)

    revenue_forecast = _revenue_input_for_period(financial, period)

    cash_forecast = None
    collections = _comparison_amount(
        cash_rows, ("cash_collections", "collections"), period, "actual"
    )
    if collections is not None:
        cash_forecast = CashCollectionsForecastInput(
            period_start=_period_date(period),
            period_end=_period_date(period),
            forecasted_collections=collections,
        )

    pipeline_changes: list[PipelineChange] = []
    for label, types in (
        ("Pipeline created", ("pipeline_created",)),
        ("Closed won", ("closed_won",)),
        ("Closed lost", ("closed_lost",)),
        ("Slipped pipeline", ("slipped_pipeline",)),
    ):
        amount = _comparison_amount(pipeline_rows, types, period, "actual")
        if amount is not None:
            pipeline_changes.append(PipelineChange(label=label, delta_arr=amount))

    # Actual vs Budget is the board's variance question; the schema field is named
    # `forecast`, so each metric label states the baseline explicitly.
    variance_rows: list[VarianceRow] = []
    if revenue_forecast is not None:
        variance_rows.append(
            _variance_row(
                "Revenue (actual vs budget)",
                revenue_forecast.actual_revenue,
                revenue_forecast.budget_revenue,
            )
        )
    for metric, movement, higher_is_better in (
        ("Ending ARR (actual vs budget)", "ending", True),
        ("New ARR (actual vs budget)", "new", True),
        ("Expansion ARR (actual vs budget)", "expansion", True),
        # Churn and contraction arrive as negative amounts, so a larger (less
        # negative) actual than budget is the favorable outcome.
        ("Churned ARR (actual vs budget)", "churn", True),
        ("Contraction ARR (actual vs budget)", "contraction", True),
    ):
        types = ARR_MOVEMENT_TYPES[movement]
        variance_rows.append(
            _variance_row(
                metric,
                _comparison_amount(arr_rows, types, period, "actual"),
                _comparison_amount(arr_rows, types, period, "budget"),
                higher_is_better=higher_is_better,
            )
        )
    variance_rows.append(
        _variance_row(
            "Ending cash (actual vs budget)",
            _comparison_amount(cash_rows, ("ending_cash",), period, "actual"),
            _comparison_amount(cash_rows, ("ending_cash",), period, "budget"),
        )
    )

    return CommentaryInputs(
        period_label=period,
        organization_name=organization_name,
        mrr_waterfall=mrr,
        revenue_forecast=revenue_forecast,
        cash_forecast=cash_forecast,
        pipeline_changes=pipeline_changes,
        actuals_vs_forecast=[row for row in variance_rows if row is not None],
    )
