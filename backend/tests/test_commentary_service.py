"""Unit tests for the AI commentary service using a mocked LLM client."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.services.commentary.openai_client import CommentaryLLMClient, LLMError
from app.services.commentary.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.commentary.schemas import (
    BookingsForecastInput,
    CashCollectionsForecastInput,
    CommentaryInputs,
    CommentaryOutput,
    CustomerMovementSummary,
    KpiTrend,
    MrrWaterfallSummary,
    PipelineChange,
    QuotaAttainment,
    RevenueForecastInput,
    SalesEfficiencyInput,
    VarianceRow,
)
from app.services.commentary.service import generate_commentary


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _well_formed_response(period_label: str = "May 2026") -> dict[str, Any]:
    """A complete, schema-conformant model response used by happy-path tests."""
    return {
        "period_label": period_label,
        "executive_summary": {
            "title": "Executive Summary",
            "narrative": "Ending MRR closed at $110,000 with NRR of 1.05.",
            "citations": [
                {"label": "ending_mrr", "value": "$110,000"},
                {"label": "NRR", "value": "1.05"},
            ],
        },
        "revenue_commentary": {
            "title": "Revenue",
            "narrative": "Revenue grew 10% over the prior period.",
            "citations": [{"label": "revenue_growth", "value": "10%"}],
        },
        "mrr_waterfall_commentary": {
            "title": "MRR Waterfall",
            "narrative": "$15k new, $5k expansion, $8k churn yielded $110k ending MRR.",
            "citations": [{"label": "new_mrr", "value": "$15,000"}],
        },
        "bookings_forecast_commentary": {
            "title": "Bookings Forecast",
            "narrative": "Pipeline coverage of 3.0x supports the base forecast.",
            "citations": [{"label": "coverage_ratio", "value": "3.0"}],
        },
        "cash_forecast_commentary": {
            "title": "Cash Forecast",
            "narrative": "Cash forecast not provided this period.",
            "citations": [],
        },
        "risks_and_opportunities": [
            {
                "type": "risk",
                "description": "Churn MRR represented 8% of beginning MRR.",
                "evidence": "$8,000 churn on $100,000 beginning MRR.",
                "severity": "medium",
            }
        ],
        "followup_questions": [
            {
                "question": "Which segments drove the $8k of churn?",
                "rationale": "Segment-level data not provided to attribute root cause.",
            }
        ],
        "data_gaps": [
            {
                "topic": "Churn root cause",
                "data_needed": "Per-customer downgrade and cancellation reasons.",
            }
        ],
    }


class FakeLLMClient:
    """In-memory fake — records the prompt and returns a canned response."""

    def __init__(self, response: dict[str, Any] | str | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        if isinstance(self.response, Exception):
            raise self.response
        if isinstance(self.response, str):
            # Simulate the SDK already JSON-decoding — strings emulate a parser failure.
            raise LLMError(self.response)
        return self.response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_inputs() -> CommentaryInputs:
    return CommentaryInputs(
        period_label="May 2026",
        organization_name="Demo Org",
        currency="USD",
        mrr_waterfall=MrrWaterfallSummary(
            period=date(2026, 5, 1),
            beginning_mrr=Decimal("100000"),
            new_mrr=Decimal("15000"),
            expansion_mrr=Decimal("5000"),
            contraction_mrr=Decimal("2000"),
            churn_mrr=Decimal("8000"),
            reactivation_mrr=Decimal("0"),
            ending_mrr=Decimal("110000"),
            nrr=Decimal("1.05"),
            grr=Decimal("0.90"),
            gross_mrr_churn_rate=Decimal("0.08"),
        ),
        bookings_forecast=BookingsForecastInput(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            total_forecast=Decimal("180000"),
            base=Decimal("180000"),
            conservative=Decimal("150000"),
            upside=Decimal("220000"),
            confidence_score=Decimal("0.72"),
            confidence_band="medium",
            coverage_ratio=Decimal("3.0"),
            target_bookings=Decimal("60000"),
        ),
        revenue_forecast=RevenueForecastInput(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            forecasted_revenue=Decimal("110000"),
            prior_period_revenue=Decimal("100000"),
            growth_rate=Decimal("0.10"),
        ),
        kpi_trends=[
            KpiTrend(period_label="Mar 2026", arr=Decimal("1100000"), nrr=Decimal("1.03")),
            KpiTrend(period_label="Apr 2026", arr=Decimal("1200000"), nrr=Decimal("1.04")),
            KpiTrend(period_label="May 2026", arr=Decimal("1320000"), nrr=Decimal("1.05")),
        ],
        actuals_vs_forecast=[
            VarianceRow(
                metric="revenue",
                actual=Decimal("110000"),
                forecast=Decimal("105000"),
                variance_absolute=Decimal("5000"),
                variance_percent=Decimal("0.048"),
                direction="favorable",
            ),
        ],
        pipeline_changes=[
            PipelineChange(label="Enterprise stage 4 -> 5", delta_arr=Decimal("120000"), delta_count=2),
        ],
        customer_movement=CustomerMovementSummary(
            new_customers=20,
            churned_customers=10,
            expanded_customers=4,
            contracted_customers=1,
            reactivated_customers=0,
        ),
        quota_attainment=[
            QuotaAttainment(
                rep_id="REP-001",
                rep_name="Alex Doe",
                segment="Enterprise",
                quota_arr=Decimal("400000"),
                closed_won_arr=Decimal("180000"),
                attainment_rate=Decimal("0.45"),
            ),
        ],
        sales_efficiency=SalesEfficiencyInput(
            new_bookings_arr=Decimal("180000"),
            sales_marketing_expense=Decimal("60000"),
            sales_efficiency=Decimal("3.0"),
            magic_number=Decimal("0.73"),
            cac_payback_months=Decimal("5.0"),
        ),
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def test_user_prompt_includes_period_and_data() -> None:
    inputs = _sample_inputs()
    prompt = build_user_prompt(inputs)
    assert "May 2026" in prompt
    assert "Demo Org" in prompt
    assert "USD" in prompt
    # Data block is embedded as JSON the model can quote from
    assert "\"ending_mrr\": \"110000\"" in prompt
    # The required output schema is pinned to the prompt
    assert "executive_summary" in prompt
    assert "risks_and_opportunities" in prompt
    assert "data_gaps" in prompt


def test_system_prompt_locks_down_invention() -> None:
    assert "Use only the numbers and facts contained in the JSON data block" in SYSTEM_PROMPT
    assert "Never speculate on causes you cannot evidence." in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_generate_commentary_happy_path() -> None:
    fake = FakeLLMClient(_well_formed_response())
    out = generate_commentary(_sample_inputs(), fake)

    assert isinstance(out, CommentaryOutput)
    assert out.period_label == "May 2026"
    assert out.executive_summary.narrative.startswith("Ending MRR")
    assert out.executive_summary.citations[0].label == "ending_mrr"
    assert len(out.risks_and_opportunities) == 1
    assert out.risks_and_opportunities[0].type == "risk"
    assert out.followup_questions[0].question.startswith("Which segments")
    assert out.data_gaps[0].topic == "Churn root cause"

    # The fake recorded a single call with both prompts
    assert len(fake.calls) == 1
    assert "ending_mrr" in fake.calls[0]["user"]
    assert fake.calls[0]["system"] is SYSTEM_PROMPT


def test_generate_commentary_forces_period_label_when_model_omits_it() -> None:
    response = _well_formed_response()
    response.pop("period_label")  # simulate model dropping the field
    fake = FakeLLMClient(response)
    out = generate_commentary(_sample_inputs(), fake)
    assert out.period_label == "May 2026"


def test_generate_commentary_preserves_data_gaps_block() -> None:
    response = _well_formed_response()
    response["data_gaps"] = [
        {"topic": "Cash collections", "data_needed": "AR aging at month-end."},
        {"topic": "Segment churn", "data_needed": "Per-segment movement breakdown."},
    ]
    fake = FakeLLMClient(response)
    out = generate_commentary(_sample_inputs(), fake)
    assert [g.topic for g in out.data_gaps] == ["Cash collections", "Segment churn"]


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_invalid_json_raises_llm_error() -> None:
    fake = FakeLLMClient(LLMError("OpenAI response was not valid JSON. ..."))
    with pytest.raises(LLMError):
        generate_commentary(_sample_inputs(), fake)


def test_non_object_response_raises_llm_error() -> None:
    class ListReturningClient:
        def generate(self, **_: Any) -> Any:
            return ["this", "should", "have", "been", "an", "object"]

    with pytest.raises(LLMError, match="Expected a JSON object"):
        generate_commentary(_sample_inputs(), ListReturningClient())


def test_schema_violation_raises_llm_error() -> None:
    # Missing required sections — Pydantic validation should fail.
    bad = {"period_label": "May 2026", "executive_summary": {"title": "x", "narrative": "y"}}
    fake = FakeLLMClient(bad)
    with pytest.raises(LLMError, match="did not conform"):
        generate_commentary(_sample_inputs(), fake)


def test_extra_unknown_fields_are_rejected() -> None:
    response = _well_formed_response()
    response["mystery_section"] = {"title": "unsupported"}
    fake = FakeLLMClient(response)
    with pytest.raises(LLMError):
        generate_commentary(_sample_inputs(), fake)


# ---------------------------------------------------------------------------
# Sparse inputs (model is allowed to skip sections)
# ---------------------------------------------------------------------------


def test_sparse_inputs_still_generate_valid_output() -> None:
    sparse = CommentaryInputs(period_label="May 2026", organization_name="Demo")
    response = _well_formed_response()
    # Simulate the model marking missing data instead of inventing it
    response["mrr_waterfall_commentary"]["narrative"] = "MRR waterfall not provided this period."
    response["mrr_waterfall_commentary"]["citations"] = []
    fake = FakeLLMClient(response)
    out = generate_commentary(sparse, fake)
    assert "not provided" in out.mrr_waterfall_commentary.narrative


# ---------------------------------------------------------------------------
# FastAPI route — uses dependency override to swap in the fake client
# ---------------------------------------------------------------------------


def test_commentary_route_uses_injected_client() -> None:
    from fastapi.testclient import TestClient

    from app.api.commentary_routes import set_llm_client_override
    from app.main import app

    fake = FakeLLMClient(_well_formed_response())
    set_llm_client_override(fake)
    try:
        client = TestClient(app)
        payload = _sample_inputs().model_dump(mode="json")
        resp = client.post("/api/v1/commentary/generate", json=payload)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["period_label"] == "May 2026"
        assert body["executive_summary"]["narrative"].startswith("Ending MRR")
        assert body["data_gaps"][0]["topic"] == "Churn root cause"
        assert len(fake.calls) == 1
    finally:
        set_llm_client_override(None)


def test_commentary_route_returns_502_on_llm_error() -> None:
    from fastapi.testclient import TestClient

    from app.api.commentary_routes import set_llm_client_override
    from app.main import app

    fake = FakeLLMClient(LLMError("OpenAI request failed: rate limit"))
    set_llm_client_override(fake)
    try:
        client = TestClient(app)
        payload = _sample_inputs().model_dump(mode="json")
        resp = client.post("/api/v1/commentary/generate", json=payload)
        assert resp.status_code == 502
        assert "rate limit" in resp.json()["detail"]
    finally:
        set_llm_client_override(None)
