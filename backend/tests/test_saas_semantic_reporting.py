"""Semantic reporting layer: movements, periods, density."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import WaterfallAttributionRow
from app.services.board_package.schemas import ChartSpec
from app.services.reporting.export.board_chart_density import prepare_chart_for_executive, thin_categories
from app.services.reporting.export.reporting_period_engine import PeriodMode, build_period_context, periods_for_mode
from app.services.reporting.export.saas_semantic_reporting import (
    OpportunityMovementType,
    build_movement_attribution,
    classify_opportunity_movement,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.dashboard.schemas import ExecutiveFlowResponse


def _bundle(**kwargs) -> ReportingBundle:
    org = "00000000-0000-0000-0000-000000000001"
    defaults = dict(
        organization_id=org,
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period="2026-05",
        period_label="May 2026",
        executive_flow=ExecutiveFlowResponse(
            organization_id=org,
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
        ),
    )
    defaults.update(kwargs)
    return ReportingBundle(**defaults)


def test_period_context_ytd_modes() -> None:
    bundle = _bundle()
    ctx = build_period_context(bundle)
    assert "2026-05" in periods_for_mode(ctx, PeriodMode.CURRENT_MONTH)
    assert len(periods_for_mode(ctx, PeriodMode.YTD)) == 5


def test_build_period_context_does_not_crash() -> None:
    """Regression: is_closed_period requires has_actual_rows."""
    bundle = _bundle()
    ctx = build_period_context(bundle)
    assert ctx.as_of == "2026-05"
    assert isinstance(ctx.closed_periods, tuple)


def test_classify_new_vs_prior_closed_won() -> None:
    row_new = WaterfallAttributionRow(
        organization_id="x",
        scenario="Actual",
        period="2026-05",
        waterfall_type="closed_won",
        opportunity_id="A1",
        arr_impact=Decimal("10000"),
        amount=Decimal("-10000"),
        source_table="t",
    )
    mt = classify_opportunity_movement(row_new, as_of="2026-05", first_created_period="2026-05")
    assert mt == OpportunityMovementType.NEW_CREATED

    row_prior = WaterfallAttributionRow(
        organization_id="x",
        scenario="Actual",
        period="2026-05",
        waterfall_type="closed_won",
        opportunity_id="A2",
        arr_impact=Decimal("20000"),
        amount=Decimal("-20000"),
        source_table="t",
    )
    mt2 = classify_opportunity_movement(row_prior, as_of="2026-05", first_created_period="2026-03")
    assert mt2 == OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON


def test_movement_attribution_from_opportunity_rows() -> None:
    bundle = _bundle(
        opportunity_attribution=[
            WaterfallAttributionRow(
                organization_id="x",
                scenario="Actual",
                period="2026-05",
                waterfall_type="pipeline_created",
                opportunity_id="O1",
                arr_impact=Decimal("5000"),
                amount=Decimal("5000"),
                source_table="t",
            ),
            WaterfallAttributionRow(
                organization_id="x",
                scenario="Actual",
                period="2026-05",
                waterfall_type="closed_won",
                opportunity_id="O2",
                arr_impact=Decimal("8000"),
                amount=Decimal("-8000"),
                source_table="t",
            ),
        ]
    )
    summary = build_movement_attribution(bundle)
    assert summary.count(OpportunityMovementType.NEW_CREATED) >= 1


def test_chart_density_thins_categories() -> None:
    cats = [f"M{i}" for i in range(12)]
    series = {"A": [float(i) for i in range(12)]}
    new_cats, new_series = thin_categories(cats, series, max_points=6)
    assert len(new_cats) <= 6
    spec = prepare_chart_for_executive(
        ChartSpec(title="Test", categories=cats, series=series),
        max_categories=6,
    )
    assert len(spec.categories) <= 6
