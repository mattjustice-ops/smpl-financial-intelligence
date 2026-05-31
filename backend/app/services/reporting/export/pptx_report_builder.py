"""Board-style PowerPoint from live reporting bundle (API-sourced data only)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.board_package.package import build_board_package, fmt_money
from app.services.board_package.schemas import (
    ArrBridge,
    BoardPackageInputs,
    CashForecastSlide,
    CompanyKpiSummary,
    MrrWaterfallSlide,
    RevenueForecastSlide,
    SlideContent,
    TableSpec,
)
from app.services.reporting.export.schemas import ReportingBundle, waterfall_by_type


def _board_inputs_from_bundle(bundle: ReportingBundle) -> BoardPackageInputs:
    as_of = bundle.as_of_period
    arr_rows = bundle.comparison_waterfalls.get("arr") or []
    arr_wf = bundle.executive_flow.waterfalls.get("arr")
    cash_wf = bundle.executive_flow.waterfalls.get("cash_flow")
    pipeline_wf = bundle.executive_flow.waterfalls.get("pipeline")

    ending_arr = Decimal("0")
    if arr_rows:
        for row in arr_rows:
            if row.period == as_of and row.waterfall_type in {"ending_arr", "ending"} and row.scenario == "Actual":
                ending_arr = row.amount
                break
    elif arr_wf:
        ending_arr = waterfall_by_type(arr_wf, "ending_arr", as_of) or waterfall_by_type(
            arr_wf, "ending_balance", as_of
        )

    kpi = CompanyKpiSummary(
        period_label=bundle.period_label,
        arr=ending_arr,
        mrr=ending_arr / Decimal("12") if ending_arr else None,
    )

    mrr_slide = None
    arr_bridge = None
    if arr_wf:
        beg = waterfall_by_type(arr_wf, "beginning_arr", as_of) or waterfall_by_type(
            arr_wf, "beginning_balance", as_of
        )
        end = waterfall_by_type(arr_wf, "ending_arr", as_of) or waterfall_by_type(
            arr_wf, "ending_balance", as_of
        )
        period_date = date(int(as_of[:4]), int(as_of[5:7]), 1)
        mrr_slide = MrrWaterfallSlide(
            period=period_date,
            beginning_mrr=beg / Decimal("12"),
            new_mrr=waterfall_by_type(arr_wf, "new_arr", as_of) / Decimal("12"),
            expansion_mrr=waterfall_by_type(arr_wf, "expansion_arr", as_of) / Decimal("12"),
            contraction_mrr=waterfall_by_type(arr_wf, "contraction_arr", as_of) / Decimal("12"),
            churn_mrr=waterfall_by_type(arr_wf, "churn_arr", as_of) / Decimal("12"),
            reactivation_mrr=waterfall_by_type(arr_wf, "reactivation_arr", as_of) / Decimal("12"),
            ending_mrr=end / Decimal("12"),
        )
        arr_bridge = ArrBridge(
            period=period_date,
            beginning_arr=beg,
            new_arr=waterfall_by_type(arr_wf, "new_arr", as_of),
            expansion_arr=waterfall_by_type(arr_wf, "expansion_arr", as_of),
            contraction_arr=waterfall_by_type(arr_wf, "contraction_arr", as_of),
            churn_arr=waterfall_by_type(arr_wf, "churn_arr", as_of),
            reactivation_arr=waterfall_by_type(arr_wf, "reactivation_arr", as_of),
            ending_arr=end,
        )

    revenue_slide = None
    if bundle.financial_statements:
        for row in bundle.financial_statements.income_statement.rows:
            if str(row.period)[:7] != as_of:
                continue
            if "revenue" in row.line_item.lower():
                revenue_slide = RevenueForecastSlide(
                    period_start=row.period,
                    period_end=row.period,
                    forecasted_revenue=row.amount if row.scenario == "Forecast" else Decimal("0"),
                    actual_revenue=row.amount if row.scenario == "Actual" else None,
                )
                break

    cash_slide = None
    if cash_wf:
        period_date = date(int(as_of[:4]), int(as_of[5:7]), 1)
        collections = Decimal("0")
        ending_cash = Decimal("0")
        for row in cash_wf.rows:
            if row.period != as_of:
                continue
            if row.waterfall_type in {"collections", "cash_in_collections"}:
                collections += row.amount
            if row.waterfall_type == "ending_cash":
                ending_cash = row.amount
        cash_slide = CashForecastSlide(
            period_start=period_date,
            period_end=period_date,
            forecasted_collections=collections,
            cash_position=ending_cash,
        )

    return BoardPackageInputs(
        organization_name=bundle.organization_name or "Organization",
        period_label=bundle.period_label,
        currency=bundle.currency,
        kpi_summary=kpi,
        mrr_waterfall=mrr_slide,
        arr_bridge=arr_bridge,
        revenue_forecast=revenue_slide,
        cash_forecast=cash_slide,
        commentary=bundle.commentary,
    )


def _extra_slides_from_bundle(bundle: ReportingBundle) -> list[SlideContent]:
    """Slides beyond the canonical 10-slide board package."""
    slides: list[SlideContent] = []
    as_of = bundle.as_of_period

    # Pipeline health
    pipeline = bundle.executive_flow.waterfalls.get("pipeline")
    if pipeline:
        rows = [
            [r.line_item, fmt_money(r.amount, bundle.currency)]
            for r in sorted(pipeline.rows, key=lambda x: (x.period, x.line_item_order))
            if r.period == as_of
        ][:12]
        slides.append(
            SlideContent(
                slide_id="pipeline_health",
                title="Pipeline Health",
                subtitle=bundle.period_label,
                table=TableSpec(headers=["Line Item", "Amount"], rows=rows) if rows else None,
                narrative="Pipeline waterfall from API (MRR waterfall is source of truth for ARR movement).",
            )
        )

    # GAAP / deferred revenue
    deferred = bundle.executive_flow.waterfalls.get("deferred_revenue")
    if deferred:
        rows = [
            [r.line_item, fmt_money(r.amount, bundle.currency)]
            for r in sorted(deferred.rows, key=lambda x: x.line_item_order)
            if r.period == as_of
        ][:14]
        slides.append(
            SlideContent(
                slide_id="gaap_revenue",
                title="GAAP Revenue Forecast",
                subtitle=bundle.period_label,
                table=TableSpec(headers=["Component", "Amount"], rows=rows) if rows else None,
            )
        )

    # Validation
    val_rows = [
        [c.validation_name, c.status, str(c.variance or "")]
        for c in bundle.validation.checks[:15]
    ]
    slides.append(
        SlideContent(
            slide_id="validation",
            title="Validation / Data Quality",
            subtitle=f"Overall: {bundle.validation.status}",
            bullets=[
                f"Passed: {bundle.validation.passed_count}",
                f"Warnings: {bundle.validation.warning_count}",
                f"Failed: {bundle.validation.failed_count}",
            ],
            table=TableSpec(headers=["Check", "Status", "Variance"], rows=val_rows) if val_rows else None,
        )
    )

    # Risks placeholder from commentary fields
    risks = [f.leadership_attention for f in bundle.commentary_fields if f.leadership_attention][:5]
    slides.append(
        SlideContent(
            slide_id="risks",
            title="Risks & Opportunities",
            subtitle=bundle.period_label,
            bullets=risks or ["Complete variance commentary in the Excel workbook export."],
        )
    )

    return slides


def build_pptx_bytes(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: str = "full_board",
) -> bytes:
    from app.services.reporting.export.board_export_service import build_board_pptx_bytes

    return build_board_pptx_bytes(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_validation_appendix,
        use_ai_commentary=use_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,  # type: ignore[arg-type]
    )
