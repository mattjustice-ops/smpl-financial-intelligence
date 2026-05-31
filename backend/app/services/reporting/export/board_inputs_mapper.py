"""Map live dashboard data to commentary / board package inputs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.commentary.schemas import CommentaryInputs, MrrWaterfallSummary, RevenueForecastInput
from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallResponse
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


def build_commentary_inputs(
    *,
    organization_name: str | None,
    as_of_period: str,
    bundle_data: ExecutiveFlowResponse,
    financial: SummaryResponse | None,
) -> CommentaryInputs:
    period = to_period(as_of_period)
    arr = bundle_data.waterfalls.get("arr")
    mrr = _arr_waterfall_for_period(arr, period)

    revenue_forecast: RevenueForecastInput | None = None
    if financial:
        for row in financial.income_statement.rows:
            if str(row.period)[:7] == period and row.line_item.lower() in {"revenue", "total revenue"}:
                revenue_forecast = RevenueForecastInput(
                    period_start=row.period,
                    period_end=row.period,
                    forecasted_revenue=row.amount if row.scenario == "Forecast" else Decimal("0"),
                    actual_revenue=row.amount if row.scenario == "Actual" else None,
                )
                break

    return CommentaryInputs(
        period_label=period,
        organization_name=organization_name,
        mrr_waterfall=mrr,
        revenue_forecast=revenue_forecast,
    )
