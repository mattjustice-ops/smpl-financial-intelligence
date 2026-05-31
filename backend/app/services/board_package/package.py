"""Build the canonical 10-slide board package from structured inputs.

Each `_build_*_slide` helper returns a `SlideContent` and gracefully handles
missing data by falling back to "Not provided this period" — never inventing
numbers. The pptx renderer and Google Slides emitter both consume the output
of `build_board_package`, so they always show identical content.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from app.services.board_package.schemas import (
    ArrBridge,
    BoardPackage,
    BoardPackageInputs,
    BookingsForecastSlide,
    CashForecastSlide,
    ChartSpec,
    ChurnExpansionAnalysis,
    CompanyKpiSummary,
    MrrWaterfallSlide,
    QuotaAttainmentRow,
    RevenueForecastSlide,
    SalesEfficiencySlide,
    SlideContent,
    TableSpec,
)
NOT_PROVIDED = "Not provided this period."


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt_money(value: Optional[Decimal], currency: str = "USD") -> str:
    if value is None:
        return "n/a"
    v = Decimal(value)
    sign = "-" if v < 0 else ""
    abs_v = abs(v)
    if abs_v >= Decimal("1000000"):
        return f"{sign}${abs_v / Decimal('1000000'):,.2f}M {currency}"
    if abs_v >= Decimal("1000"):
        return f"{sign}${abs_v / Decimal('1000'):,.1f}K {currency}"
    return f"{sign}${abs_v:,.2f} {currency}"


def fmt_pct(value: Optional[Decimal]) -> str:
    if value is None:
        return "n/a"
    return f"{Decimal(value) * 100:.1f}%"


def fmt_ratio(value: Optional[Decimal]) -> str:
    if value is None:
        return "n/a"
    return f"{Decimal(value):.2f}x"


def fmt_int(value: Optional[int]) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def fmt_months(value: Optional[Decimal]) -> str:
    if value is None:
        return "n/a"
    return f"{Decimal(value):.1f} mo"


def _to_float(v: Optional[Decimal]) -> float:
    return float(v) if v is not None else 0.0


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------


def _build_executive_summary_slide(
    inputs: BoardPackageInputs,
) -> SlideContent:
    kpi = inputs.kpi_summary
    commentary = inputs.commentary
    bullets: list[str] = []

    if kpi:
        bullets.extend(
            line
            for line in [
                f"ARR: {fmt_money(kpi.arr, inputs.currency)} "
                f"(MRR {fmt_money(kpi.mrr, inputs.currency)})",
                f"NRR: {fmt_pct(kpi.nrr)} | GRR: {fmt_pct(kpi.grr)}",
                f"Rule of 40: {fmt_pct(kpi.rule_of_40)} | "
                f"Magic Number: {fmt_ratio(kpi.magic_number)}",
                f"Pipeline coverage: {fmt_ratio(kpi.pipeline_coverage)} | "
                f"Burn multiple: {fmt_ratio(kpi.burn_multiple)}",
            ]
            if line
        )

    narrative: Optional[str] = None
    if commentary:
        narrative = commentary.executive_summary.narrative
    elif not bullets:
        narrative = NOT_PROVIDED

    return SlideContent(
        slide_id="executive_summary",
        title="Executive Summary",
        subtitle=f"{inputs.organization_name} — {inputs.period_label}",
        narrative=narrative,
        bullets=bullets,
        footnote="All figures are based solely on supplied data.",
    )


def _build_revenue_slide(inputs: BoardPackageInputs) -> SlideContent:
    rev = inputs.revenue_forecast
    commentary = inputs.commentary

    bullets: list[str] = []
    table: Optional[TableSpec] = None
    chart: Optional[ChartSpec] = None

    if rev:
        bullets = [
            f"Forecasted revenue: {fmt_money(rev.forecasted_revenue, inputs.currency)}",
            f"Actual revenue: {fmt_money(rev.actual_revenue, inputs.currency)}",
            f"Prior period revenue: {fmt_money(rev.prior_period_revenue, inputs.currency)}",
            f"Growth rate: {fmt_pct(rev.growth_rate)}",
        ]
        if rev.variance_vs_plan is not None:
            bullets.append(f"Variance vs plan: {fmt_money(rev.variance_vs_plan, inputs.currency)}")
        table = TableSpec(
            headers=["Metric", "Value"],
            rows=[
                ["Forecasted revenue", fmt_money(rev.forecasted_revenue, inputs.currency)],
                ["Actual revenue", fmt_money(rev.actual_revenue, inputs.currency)],
                ["Prior period revenue", fmt_money(rev.prior_period_revenue, inputs.currency)],
                ["Growth rate", fmt_pct(rev.growth_rate)],
            ],
        )
        chart = ChartSpec(
            chart_type="column",
            title="Revenue: Prior vs Current vs Forecast",
            categories=["Prior", "Actual", "Forecast"],
            series={
                "Revenue": [
                    _to_float(rev.prior_period_revenue),
                    _to_float(rev.actual_revenue),
                    _to_float(rev.forecasted_revenue),
                ],
            },
        )
    return SlideContent(
        slide_id="revenue_performance",
        title="Revenue Performance",
        subtitle=inputs.period_label,
        narrative=commentary.revenue_commentary.narrative if commentary else None,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
        chart=chart,
    )


def _build_mrr_waterfall_slide(inputs: BoardPackageInputs) -> SlideContent:
    mrr = inputs.mrr_waterfall
    commentary = inputs.commentary
    bullets: list[str] = []
    table: Optional[TableSpec] = None
    chart: Optional[ChartSpec] = None

    if mrr:
        bullets = [
            f"Beginning MRR: {fmt_money(mrr.beginning_mrr, inputs.currency)}",
            f"+ New: {fmt_money(mrr.new_mrr, inputs.currency)} | "
            f"+ Expansion: {fmt_money(mrr.expansion_mrr, inputs.currency)} | "
            f"+ Reactivation: {fmt_money(mrr.reactivation_mrr, inputs.currency)}",
            f"- Contraction: {fmt_money(mrr.contraction_mrr, inputs.currency)} | "
            f"- Churn: {fmt_money(mrr.churn_mrr, inputs.currency)}",
            f"Ending MRR: {fmt_money(mrr.ending_mrr, inputs.currency)}",
            f"NRR: {fmt_pct(mrr.nrr)} | GRR: {fmt_pct(mrr.grr)}",
        ]
        table = TableSpec(
            headers=["Movement", inputs.currency],
            rows=[
                ["Beginning MRR", fmt_money(mrr.beginning_mrr, inputs.currency)],
                ["New", fmt_money(mrr.new_mrr, inputs.currency)],
                ["Expansion", fmt_money(mrr.expansion_mrr, inputs.currency)],
                ["Reactivation", fmt_money(mrr.reactivation_mrr, inputs.currency)],
                ["Contraction", f"({fmt_money(mrr.contraction_mrr, inputs.currency)})"],
                ["Churn", f"({fmt_money(mrr.churn_mrr, inputs.currency)})"],
                ["Ending MRR", fmt_money(mrr.ending_mrr, inputs.currency)],
            ],
        )
        chart = ChartSpec(
            chart_type="waterfall",
            title="MRR Waterfall",
            categories=["Beginning", "New", "Expansion", "Reactivation", "Contraction", "Churn", "Ending"],
            series={
                "MRR": [
                    _to_float(mrr.beginning_mrr),
                    _to_float(mrr.new_mrr),
                    _to_float(mrr.expansion_mrr),
                    _to_float(mrr.reactivation_mrr),
                    -_to_float(mrr.contraction_mrr),
                    -_to_float(mrr.churn_mrr),
                    _to_float(mrr.ending_mrr),
                ]
            },
        )
    return SlideContent(
        slide_id="mrr_waterfall",
        title="MRR Waterfall",
        subtitle=inputs.period_label,
        narrative=commentary.mrr_waterfall_commentary.narrative if commentary else None,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
        chart=chart,
    )


def _build_arr_bridge_slide(inputs: BoardPackageInputs) -> SlideContent:
    arr = inputs.arr_bridge
    bullets: list[str] = []
    table: Optional[TableSpec] = None
    chart: Optional[ChartSpec] = None

    if arr:
        net_new = (
            arr.new_arr + arr.expansion_arr + arr.reactivation_arr
            - arr.contraction_arr - arr.churn_arr
        )
        bullets = [
            f"Beginning ARR: {fmt_money(arr.beginning_arr, inputs.currency)}",
            f"Net new ARR: {fmt_money(net_new, inputs.currency)}",
            f"Ending ARR: {fmt_money(arr.ending_arr, inputs.currency)}",
        ]
        table = TableSpec(
            headers=["Component", inputs.currency],
            rows=[
                ["Beginning ARR", fmt_money(arr.beginning_arr, inputs.currency)],
                ["New ARR", fmt_money(arr.new_arr, inputs.currency)],
                ["Expansion ARR", fmt_money(arr.expansion_arr, inputs.currency)],
                ["Reactivation ARR", fmt_money(arr.reactivation_arr, inputs.currency)],
                ["Contraction ARR", f"({fmt_money(arr.contraction_arr, inputs.currency)})"],
                ["Churn ARR", f"({fmt_money(arr.churn_arr, inputs.currency)})"],
                ["Net new ARR", fmt_money(net_new, inputs.currency)],
                ["Ending ARR", fmt_money(arr.ending_arr, inputs.currency)],
            ],
        )
        chart = ChartSpec(
            chart_type="waterfall",
            title="ARR Bridge",
            categories=["Beginning", "New", "Expansion", "Reactivation", "Contraction", "Churn", "Ending"],
            series={
                "ARR": [
                    _to_float(arr.beginning_arr),
                    _to_float(arr.new_arr),
                    _to_float(arr.expansion_arr),
                    _to_float(arr.reactivation_arr),
                    -_to_float(arr.contraction_arr),
                    -_to_float(arr.churn_arr),
                    _to_float(arr.ending_arr),
                ]
            },
        )

    return SlideContent(
        slide_id="arr_bridge",
        title="ARR Bridge",
        subtitle=inputs.period_label,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
        chart=chart,
    )


def _build_bookings_forecast_slide(inputs: BoardPackageInputs) -> SlideContent:
    bf = inputs.bookings_forecast
    commentary = inputs.commentary
    bullets: list[str] = []
    table: Optional[TableSpec] = None
    chart: Optional[ChartSpec] = None

    if bf:
        bullets = [
            f"Period: {bf.period_start.isoformat()} to {bf.period_end.isoformat()}",
            f"Total forecast: {fmt_money(bf.total_forecast, inputs.currency)}",
            f"Conservative / Base / Upside: "
            f"{fmt_money(bf.conservative, inputs.currency)} / "
            f"{fmt_money(bf.base, inputs.currency)} / "
            f"{fmt_money(bf.upside, inputs.currency)}",
            f"Confidence: {fmt_pct(bf.confidence_score)} ({bf.confidence_band or 'n/a'})",
        ]
        if bf.target_bookings is not None:
            bullets.append(f"Target: {fmt_money(bf.target_bookings, inputs.currency)}")

        table = TableSpec(
            headers=["Method / Scenario", inputs.currency],
            rows=[
                ["Weighted", fmt_money(bf.weighted_forecast, inputs.currency)],
                ["Stage-adjusted", fmt_money(bf.stage_adjusted_forecast, inputs.currency)],
                ["Historical", fmt_money(bf.historical_forecast, inputs.currency)],
                ["Conservative", fmt_money(bf.conservative, inputs.currency)],
                ["Base", fmt_money(bf.base, inputs.currency)],
                ["Upside", fmt_money(bf.upside, inputs.currency)],
                ["Total forecast", fmt_money(bf.total_forecast, inputs.currency)],
            ],
        )
        chart = ChartSpec(
            chart_type="column",
            title="Bookings Forecast Scenarios",
            categories=["Conservative", "Base", "Upside"],
            series={
                "Forecast": [
                    _to_float(bf.conservative),
                    _to_float(bf.base),
                    _to_float(bf.upside),
                ]
            },
        )

    return SlideContent(
        slide_id="bookings_forecast",
        title="Bookings Forecast",
        subtitle=inputs.period_label,
        narrative=commentary.bookings_forecast_commentary.narrative if commentary else None,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
        chart=chart,
    )


def _build_pipeline_coverage_slide(inputs: BoardPackageInputs) -> SlideContent:
    bf = inputs.bookings_forecast
    kpi = inputs.kpi_summary
    bullets: list[str] = []
    table: Optional[TableSpec] = None

    coverage = None
    target = None
    pipeline = None
    if bf:
        coverage = bf.coverage_ratio
        target = bf.target_bookings
        pipeline = bf.total_pipeline
    if kpi and coverage is None:
        coverage = kpi.pipeline_coverage

    if coverage is not None or target is not None or pipeline is not None:
        bullets = [
            f"Coverage ratio: {fmt_ratio(coverage)}",
            f"Total pipeline: {fmt_money(pipeline, inputs.currency)}",
            f"Target bookings: {fmt_money(target, inputs.currency)}",
        ]
        table = TableSpec(
            headers=["Metric", "Value"],
            rows=[
                ["Total pipeline", fmt_money(pipeline, inputs.currency)],
                ["Target bookings", fmt_money(target, inputs.currency)],
                ["Coverage ratio", fmt_ratio(coverage)],
            ],
        )

    footnote = "Healthy SaaS pipeline coverage is typically 3.0x or higher."
    return SlideContent(
        slide_id="pipeline_coverage",
        title="Pipeline Coverage",
        subtitle=inputs.period_label,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
        footnote=footnote,
    )


def _build_retention_slide(inputs: BoardPackageInputs) -> SlideContent:
    ce = inputs.churn_expansion
    mrr = inputs.mrr_waterfall
    kpi = inputs.kpi_summary
    bullets: list[str] = []
    table: Optional[TableSpec] = None

    nrr = (mrr.nrr if mrr else None) or (kpi.nrr if kpi else None)
    grr = (mrr.grr if mrr else None) or (kpi.grr if kpi else None)
    gross_churn = kpi.gross_mrr_churn_rate if kpi else None
    logo_churn = kpi.logo_churn_rate if kpi else None
    net_churn = kpi.net_mrr_churn_rate if kpi else None

    if ce or mrr or kpi:
        bullets = [
            f"NRR: {fmt_pct(nrr)} | GRR: {fmt_pct(grr)}",
            f"Gross MRR churn: {fmt_pct(gross_churn)} | Logo churn: {fmt_pct(logo_churn)} | "
            f"Net MRR churn: {fmt_pct(net_churn)}",
        ]
        if ce:
            bullets.extend(
                [
                    f"Customer movement — new: {fmt_int(ce.new_customers)}, "
                    f"expanded: {fmt_int(ce.expanded_customers)}, "
                    f"contracted: {fmt_int(ce.contracted_customers)}, "
                    f"churned: {fmt_int(ce.churned_customers)}, "
                    f"reactivated: {fmt_int(ce.reactivated_customers)}",
                ]
            )
            if ce.notable_movements:
                bullets.append("Notable: " + "; ".join(ce.notable_movements))

        table = TableSpec(
            headers=["Metric", "Value"],
            rows=[
                ["NRR", fmt_pct(nrr)],
                ["GRR", fmt_pct(grr)],
                ["Gross MRR churn", fmt_pct(gross_churn)],
                ["Logo churn", fmt_pct(logo_churn)],
                ["Net MRR churn", fmt_pct(net_churn)],
            ],
        )

    return SlideContent(
        slide_id="retention_churn_expansion",
        title="Retention, Churn & Expansion",
        subtitle=inputs.period_label,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
    )


def _build_cash_forecast_slide(inputs: BoardPackageInputs) -> SlideContent:
    cf = inputs.cash_forecast
    commentary = inputs.commentary
    bullets: list[str] = []
    table: Optional[TableSpec] = None

    if cf:
        bullets = [
            f"Forecasted collections: {fmt_money(cf.forecasted_collections, inputs.currency)}",
            f"Open AR balance: {fmt_money(cf.open_ar_balance, inputs.currency)}",
            f"Expected DSO: {Decimal(cf.expected_dso):.0f} days" if cf.expected_dso is not None else "Expected DSO: n/a",
            f"Cash position: {fmt_money(cf.cash_position, inputs.currency)}",
            f"Runway: {fmt_months(cf.runway_months)}",
        ]
        rows: list[list[str]] = [
            ["Forecasted collections", fmt_money(cf.forecasted_collections, inputs.currency)],
            ["Open AR balance", fmt_money(cf.open_ar_balance, inputs.currency)],
            ["Cash position", fmt_money(cf.cash_position, inputs.currency)],
            ["Runway (months)", fmt_months(cf.runway_months)],
        ]
        for bucket, amount in cf.aging_buckets.items():
            rows.append([f"AR aging — {bucket}", fmt_money(amount, inputs.currency)])
        table = TableSpec(headers=["Metric", "Value"], rows=rows)

    return SlideContent(
        slide_id="cash_forecast",
        title="Cash Forecast",
        subtitle=inputs.period_label,
        narrative=commentary.cash_forecast_commentary.narrative if commentary else None,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
    )


def _build_sales_efficiency_slide(inputs: BoardPackageInputs) -> SlideContent:
    se = inputs.sales_efficiency
    quotas = inputs.quota_attainment
    bullets: list[str] = []
    table: Optional[TableSpec] = None

    if se:
        bullets = [
            f"New bookings ARR: {fmt_money(se.new_bookings_arr, inputs.currency)}",
            f"S&M expense: {fmt_money(se.sales_marketing_expense, inputs.currency)}",
            f"Sales efficiency: {fmt_ratio(se.sales_efficiency)}",
            f"Magic Number: {fmt_ratio(se.magic_number)}",
            f"CAC: {fmt_money(se.cac, inputs.currency)} | "
            f"CAC payback: {fmt_months(se.cac_payback_months)}",
        ]

    if quotas:
        rows = [
            [
                q.rep_id,
                q.rep_name or "—",
                q.segment or "—",
                fmt_money(q.quota_arr, inputs.currency),
                fmt_money(q.closed_won_arr, inputs.currency),
                fmt_pct(q.attainment_rate),
            ]
            for q in quotas
        ]
        table = TableSpec(
            headers=["Rep ID", "Name", "Segment", "Quota", "Closed Won", "Attainment"],
            rows=rows,
        )
    elif se:
        table = TableSpec(
            headers=["Metric", "Value"],
            rows=[
                ["New bookings ARR", fmt_money(se.new_bookings_arr, inputs.currency)],
                ["S&M expense", fmt_money(se.sales_marketing_expense, inputs.currency)],
                ["Sales efficiency", fmt_ratio(se.sales_efficiency)],
                ["Magic Number", fmt_ratio(se.magic_number)],
                ["CAC", fmt_money(se.cac, inputs.currency)],
                ["CAC payback", fmt_months(se.cac_payback_months)],
            ],
        )

    return SlideContent(
        slide_id="sales_efficiency",
        title="Sales Efficiency & Quota Attainment",
        subtitle=inputs.period_label,
        bullets=bullets or [NOT_PROVIDED],
        table=table,
    )


def _build_risks_opportunities_slide(inputs: BoardPackageInputs) -> SlideContent:
    commentary = inputs.commentary
    bullets: list[str] = []
    footnote: Optional[str] = None

    if commentary:
        for item in commentary.risks_and_opportunities:
            tag = "RISK" if item.type == "risk" else "OPPORTUNITY"
            sev = f" [{item.severity.upper()}]" if item.severity else ""
            bullets.append(f"{tag}{sev}: {item.description} — Evidence: {item.evidence}")
        if commentary.followup_questions:
            bullets.append("")
            bullets.append("Follow-up questions for finance leadership:")
            bullets.extend(f"• {q.question}" for q in commentary.followup_questions[:5])
        if commentary.data_gaps:
            footnote = "Data gaps: " + "; ".join(
                f"{g.topic} ({g.data_needed})" for g in commentary.data_gaps[:3]
            )

    return SlideContent(
        slide_id="risks_and_opportunities",
        title="Key Risks & Opportunities",
        subtitle=inputs.period_label,
        bullets=bullets or [NOT_PROVIDED],
        footnote=footnote,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_board_package(inputs: BoardPackageInputs) -> BoardPackage:
    """Assemble the canonical 10-slide structure for downstream renderers."""
    slides = [
        _build_executive_summary_slide(inputs),
        _build_revenue_slide(inputs),
        _build_mrr_waterfall_slide(inputs),
        _build_arr_bridge_slide(inputs),
        _build_bookings_forecast_slide(inputs),
        _build_pipeline_coverage_slide(inputs),
        _build_retention_slide(inputs),
        _build_cash_forecast_slide(inputs),
        _build_sales_efficiency_slide(inputs),
        _build_risks_opportunities_slide(inputs),
    ]
    return BoardPackage(
        period_label=inputs.period_label,
        organization_name=inputs.organization_name,
        prepared_for=inputs.prepared_for,
        prepared_date=inputs.prepared_date or date.today(),
        currency=inputs.currency,
        slides=slides,
    )
