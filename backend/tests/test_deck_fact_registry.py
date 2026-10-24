"""Every deck metric is one fact, and a bridge that misses is reported."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.reporting.export.deck_fact_registry import attach_deck_facts, build_fact_registry
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle


def _wf(period: str, wtype: str, amount: str, scenario: str = "Actual") -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id="test-org",
        scenario=scenario,
        period=period,
        waterfall_name="arr",
        waterfall_type=wtype,
        line_item=wtype,
        line_item_order=0,
        amount=Decimal(amount),
        source_table="test",
    )


def _bundle(ending: str = "85308000") -> ReportingBundle:
    as_of = "2026-06"
    rows = [
        _wf(as_of, "beginning_arr", "83450000"),
        _wf(as_of, "new_business", "1680000"),
        _wf(as_of, "expansion", "869100"),
        _wf(as_of, "reactivation", "142900"),
        _wf(as_of, "contraction", "313700"),
        _wf(as_of, "churn", "520200"),
        _wf(as_of, "ending_arr", ending),
        _wf(as_of, "pipeline_created", "3680000"),
        _wf(as_of, "pipeline_created", "8420000", scenario="Budget"),
    ]
    return ReportingBundle(
        organization_id="test-org",
        organization_name="Test Co",
        scenario="Combined",
        period_label="June 2026",
        as_of_period=as_of,
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="test-org",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period=as_of,
        ),
        comparison_waterfalls={"arr": rows, "pipeline": rows},
        validation=ExportValidationSummary(status="pass", failed_count=0, warning_count=0, passed_count=0, checks=[]),
    )


def test_arr_bridge_residual_is_reported() -> None:
    built = build_fact_registry(_bundle())
    tie = next(item for item in built["ties"] if item["id"] == "arr.bridge")
    assert tie["ok"] is False
    assert "does not tie" in tie["detail"]
    ids = {fact["id"] for fact in built["facts"]}
    assert "arr.ending" in ids
    assert "arr.net_new" in ids
    assert "pipeline.created" in ids
    assert "arr.gross_retention" in ids


def test_arr_bridge_ties_when_the_ending_matches() -> None:
    built = build_fact_registry(_bundle(ending="85308100"))
    tie = next(item for item in built["ties"] if item["id"] == "arr.bridge")
    assert tie["ok"] is True


def test_pipeline_created_is_one_value_and_coverage_is_not_pipeline_over_arr() -> None:
    payload = {"arr_analysis": {"pipeline_coverage_x": "0.1x"}, "gtm_performance": {"total_pipeline": "$2.95M"}, "board_actions": []}
    attach_deck_facts(payload, _bundle())
    created = next(fact for fact in payload["facts"] if fact["id"] == "pipeline.created")
    assert created["display"] == payload["gtm_performance"]["total_pipeline"]
    assert payload["arr_analysis"]["pipeline_coverage_x"] == "n/m"
    assert payload["board_actions_note"] == "No asks were entered for this close."
    assert payload["deck_profile"]["id"] == "smpl-standard"


def test_coverage_is_open_pipeline_over_new_business_still_ahead() -> None:
    bundle = _bundle()
    rows = list(bundle.comparison_waterfalls["arr"])
    rows.append(_wf("2026-06", "ending_pipeline", "6000000"))
    rows.append(_wf("2026-06", "new_business", "500000", scenario="Budget"))
    rows.append(_wf("2026-07", "new_business", "2000000", scenario="Budget"))
    rows.append(_wf("2026-08", "new_business", "1000000", scenario="Budget"))
    bundle = bundle.model_copy(update={"comparison_waterfalls": {"arr": rows, "pipeline": rows}})
    built = build_fact_registry(bundle)
    coverage = next(fact for fact in built["facts"] if fact["id"] == "pipeline.coverage")
    assert coverage["display"] == "2.0x"
    assert coverage["status"] == "on plan"


def test_a_margin_uses_a_percent_band_not_the_dollar_floor() -> None:
    from app.services.reporting.export.deck_fact_registry import _status

    assert _status(Decimal("39.8"), Decimal("75"), favorable_up=True, money=False) == "behind"
    assert _status(Decimal("74.5"), Decimal("75"), favorable_up=True, money=False) == "on plan"


def test_a_small_budget_does_not_offer_a_percent() -> None:
    built = build_fact_registry(_bundle())
    created = next(fact for fact in built["facts"] if fact["id"] == "pipeline.created")
    assert created["value"] == 3680000
    assert created["status"] == "behind"
    assert created["percent_offered"] is True
