"""Tests for P15 fail-closed attribution / driver claim verification."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.commentary.attribution_verify import (
    DONT_KNOW_ATTRIBUTION,
    AllowedDriver,
    apply_fail_closed_attribution_to_commentary,
    build_attribution_package_from_commentary_inputs,
    extract_attribution_claims,
    fail_closed_attribution_text,
    verify_text_attribution,
)
from app.services.commentary.schemas import (
    CommentaryInputs,
    CommentaryOutput,
    CommentarySection,
    MrrWaterfallSummary,
)
from app.services.commentary.service import generate_commentary


class FakeLLMClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.response


def _section(narrative: str) -> CommentarySection:
    return CommentarySection(title="t", narrative=narrative, citations=[])


def _output_with_narrative(narrative: str) -> CommentaryOutput:
    empty = _section("No material change stated.")
    return CommentaryOutput(
        period_label="May 2026",
        executive_summary=_section(narrative),
        revenue_commentary=empty,
        mrr_waterfall_commentary=empty,
        bookings_forecast_commentary=empty,
        cash_forecast_commentary=empty,
    )


def test_extract_causal_phrases() -> None:
    text = "Net new ARR of $2.7M was driven by expansion. Cash dipped due to payroll."
    claims = extract_attribution_claims(text)
    phrases = {c.phrase.lower() for c in claims}
    assert any("expansion" in p for p in phrases)
    assert any("payroll" in p for p in phrases)


def test_allowed_driver_passes() -> None:
    allowlist = [
        AllowedDriver(
            id="expansion_mrr",
            label="Expansion MRR",
            aliases=("expansion", "expansion mrr"),
        )
    ]
    text = "Ending MRR growth was driven by expansion."
    result = verify_text_attribution(text, allowlist)
    assert result.ok
    assert result.checks
    assert result.checks[0].matched_driver_id == "expansion_mrr"


def test_invented_driver_fails_closed() -> None:
    allowlist = [
        AllowedDriver(
            id="expansion_mrr",
            label="Expansion MRR",
            aliases=("expansion", "expansion mrr"),
        )
    ]
    text = (
        "Net new ARR of $2.7M was driven by three enterprise upsells."
    )
    result = verify_text_attribution(text, allowlist)
    assert not result.ok
    assert any(c.status == "off_allowlist" for c in result.failures)
    assert fail_closed_attribution_text(text, result) == DONT_KNOW_ATTRIBUTION


def test_empty_allowlist_strips_causal_claims() -> None:
    text = "ARR grew due to paid search."
    result = verify_text_attribution(text, [])
    assert not result.ok
    assert any(c.status == "empty_allowlist" for c in result.failures)


def test_numeric_only_text_unaffected() -> None:
    allowlist = [
        AllowedDriver(id="ending_mrr", label="Ending MRR", aliases=("ending mrr",))
    ]
    text = "Ending MRR closed at $110,000 with NRR of 1.05 and growth of 10%."
    result = verify_text_attribution(text, allowlist)
    assert result.ok
    assert result.checks == []
    assert fail_closed_attribution_text(text, result) == text


def test_commentary_inputs_build_waterfall_allowlist() -> None:
    pkg = build_attribution_package_from_commentary_inputs(
        CommentaryInputs(
            period_label="May 2026",
            mrr_waterfall=MrrWaterfallSummary(
                period=date(2026, 5, 1),
                beginning_mrr=Decimal("100000"),
                expansion_mrr=Decimal("8000"),
                ending_mrr=Decimal("110000"),
            ),
        )
    )
    ids = {d["id"] for d in pkg["allowed_drivers"]}
    assert "expansion_mrr" in ids
    assert "ending_mrr" in ids


def test_apply_fail_closed_rewrites_bad_attribution_section_only() -> None:
    allowlist = build_attribution_package_from_commentary_inputs(
        CommentaryInputs(
            period_label="May 2026",
            mrr_waterfall=MrrWaterfallSummary(
                period=date(2026, 5, 1),
                beginning_mrr=Decimal("100000"),
                expansion_mrr=Decimal("8000"),
                ending_mrr=Decimal("110000"),
            ),
        )
    )
    output = CommentaryOutput(
        period_label="May 2026",
        executive_summary=_section(
            "Ending MRR closed at $110,000 driven by expansion."
        ),
        revenue_commentary=_section(
            "Revenue grew due to three enterprise upsells."
        ),
        mrr_waterfall_commentary=_section("Ending MRR was $110,000."),
        bookings_forecast_commentary=_section("Bookings outlook unchanged."),
        cash_forecast_commentary=_section("Collections outlook unchanged."),
    )
    verified, result = apply_fail_closed_attribution_to_commentary(output, allowlist)
    assert not result.ok
    assert "expansion" in verified.executive_summary.narrative.lower()
    assert verified.revenue_commentary.narrative == DONT_KNOW_ATTRIBUTION
    assert verified.mrr_waterfall_commentary.narrative == "Ending MRR was $110,000."


def test_generate_embeds_attribution_and_strips_invented_driver() -> None:
    inputs = CommentaryInputs(
        period_label="May 2026",
        mrr_waterfall=MrrWaterfallSummary(
            period=date(2026, 5, 1),
            beginning_mrr=Decimal("100000"),
            expansion_mrr=Decimal("8000"),
            new_mrr=Decimal("2000"),
            ending_mrr=Decimal("110000"),
            nrr=Decimal("1.05"),
        ),
    )
    response = {
        "period_label": "May 2026",
        "executive_summary": {
            "title": "Executive Summary",
            "narrative": "Ending MRR closed at $110,000 driven by three enterprise upsells.",
            "citations": [{"label": "ending_mrr", "value": "$110,000"}],
        },
        "revenue_commentary": {
            "title": "Revenue",
            "narrative": "Revenue commentary deferred.",
            "citations": [],
        },
        "mrr_waterfall_commentary": {
            "title": "MRR",
            "narrative": "Ending MRR was $110,000.",
            "citations": [],
        },
        "bookings_forecast_commentary": {
            "title": "Bookings",
            "narrative": "Bookings inputs limited.",
            "citations": [],
        },
        "cash_forecast_commentary": {
            "title": "Cash",
            "narrative": "Cash inputs limited.",
            "citations": [],
        },
        "risks_and_opportunities": [],
        "followup_questions": [],
        "data_gaps": [],
    }
    fake = FakeLLMClient(response)
    out = generate_commentary(inputs, fake)
    assert "ATTRIBUTION PACKAGE" in fake.calls[0]["user"]
    assert out.executive_summary.narrative == DONT_KNOW_ATTRIBUTION
