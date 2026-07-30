"""Tests for P15 fail-closed numeric claim verification."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.commentary.claim_verify import (
    DONT_KNOW_NARRATIVE,
    TOL_ACTUALS,
    apply_fail_closed_to_commentary,
    build_evidence_package,
    extract_numeric_claims,
    fail_closed_text,
    verify_text_against_evidence,
)
from app.services.commentary.schemas import (
    CommentaryInputs,
    CommentaryOutput,
    CommentarySection,
    MrrWaterfallSummary,
)
from app.services.commentary.service import generate_commentary
from app.services.commentary.claim_verify import CommentaryIntegrityError
from app.services.reporting.export.board_platform_metrics import (
    verify_variance_commentary_tieout,
)


def test_tol_actuals_is_one_dollar() -> None:
    assert TOL_ACTUALS == Decimal("1.00")


def test_extract_money_percent_and_ratio() -> None:
    text = "Ending MRR closed at $110,000 with NRR of 1.05 and growth of 10%. Coverage 3.0x. New $15k."
    claims = extract_numeric_claims(text)
    kinds = {c.kind for c in claims}
    assert "money" in kinds
    assert "percent" in kinds
    assert "ratio" in kinds
    money_vals = {c.value for c in claims if c.kind == "money"}
    assert Decimal("110000") in money_vals
    assert Decimal("15000") in money_vals


def test_matching_numbers_pass() -> None:
    evidence = {
        "ending_mrr": Decimal("110000"),
        "nrr": Decimal("1.05"),
        "growth_rate": Decimal("0.10"),
    }
    text = "Ending MRR closed at $110,000 with NRR of 1.05 and growth of 10%."
    result = verify_text_against_evidence(text, evidence)
    assert result.ok
    assert result.failures == []


def test_invented_numbers_fail_closed() -> None:
    evidence = {"ending_mrr": Decimal("110000")}
    text = "ARR exploded to $99,000,000 this month."
    result = verify_text_against_evidence(text, evidence)
    assert not result.ok
    assert result.mismatch_count >= 1
    assert fail_closed_text(text, result) == DONT_KNOW_NARRATIVE


def test_missing_evidence_omits_claim() -> None:
    text = "Revenue was $5,000,000."
    result = verify_text_against_evidence(text, {})
    assert not result.ok
    assert result.missing_evidence_count >= 1
    assert fail_closed_text(text, result) == DONT_KNOW_NARRATIVE


def test_money_tolerance_cannot_be_loosened() -> None:
    with pytest.raises(ValueError, match="TOL_ACTUALS"):
        verify_text_against_evidence("$100", {"a": Decimal("100")}, money_tolerance=Decimal("1000"))


def test_apply_fail_closed_rewrites_bad_sections_only() -> None:
    evidence = build_evidence_package(
        CommentaryInputs(
            period_label="May 2026",
            mrr_waterfall=MrrWaterfallSummary(
                period=date(2026, 5, 1),
                beginning_mrr=Decimal("100000"),
                ending_mrr=Decimal("110000"),
                nrr=Decimal("1.05"),
            ),
        )
    )
    output = CommentaryOutput(
        period_label="May 2026",
        executive_summary=CommentarySection(
            title="Executive Summary",
            narrative="Ending MRR closed at $110,000 with NRR of 1.05.",
            citations=[{"label": "ending_mrr", "value": "$110,000"}],
        ),
        revenue_commentary=CommentarySection(
            title="Revenue",
            narrative="Phantom revenue hit $77,000,000.",
            citations=[],
        ),
        mrr_waterfall_commentary=CommentarySection(
            title="MRR", narrative="MRR waterfall not provided this period.", citations=[]
        ),
        bookings_forecast_commentary=CommentarySection(
            title="Bookings", narrative="Bookings forecast not provided this period.", citations=[]
        ),
        cash_forecast_commentary=CommentarySection(
            title="Cash", narrative="Cash forecast not provided this period.", citations=[]
        ),
    )
    verified, result = apply_fail_closed_to_commentary(output, evidence)
    assert not result.ok
    assert "110,000" in verified.executive_summary.narrative
    assert verified.revenue_commentary.narrative == DONT_KNOW_NARRATIVE


class _Fake:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.response


def test_generate_commentary_embeds_evidence_and_strips_invented() -> None:
    inputs = CommentaryInputs(
        period_label="May 2026",
        organization_name="Demo",
        mrr_waterfall=MrrWaterfallSummary(
            period=date(2026, 5, 1),
            beginning_mrr=Decimal("100000"),
            ending_mrr=Decimal("110000"),
            nrr=Decimal("1.05"),
        ),
    )
    response = {
        "period_label": "May 2026",
        "executive_summary": {
            "title": "Executive Summary",
            "narrative": "Ending MRR closed at $110,000.",
            "citations": [{"label": "ending_mrr", "value": "$110,000"}],
        },
        "revenue_commentary": {
            "title": "Revenue",
            "narrative": "Invented bookings of $888,000,000.",
            "citations": [],
        },
        "mrr_waterfall_commentary": {
            "title": "MRR",
            "narrative": "NRR of 1.05 on ending MRR $110,000.",
            "citations": [],
        },
        "bookings_forecast_commentary": {
            "title": "Bookings",
            "narrative": "Bookings forecast not provided this period.",
            "citations": [],
        },
        "cash_forecast_commentary": {
            "title": "Cash",
            "narrative": "Cash forecast not provided this period.",
            "citations": [],
        },
        "risks_and_opportunities": [],
        "followup_questions": [],
        "data_gaps": [],
    }
    fake = _Fake(response)
    out = generate_commentary(inputs, fake)
    assert "EVIDENCE PACKAGE" in fake.calls[0]["user"]
    assert "110,000" in out.executive_summary.narrative
    assert out.revenue_commentary.narrative == DONT_KNOW_NARRATIVE


def test_variance_tieout_fail_closed_on_mismatch() -> None:
    display = {
        "rows": [
            {
                "row_id": "vc_revenue",
                "cm": {"actual": "$100", "budget": "$90", "var": "$10"},
                "qtd": {"actual": "", "budget": "", "var": ""},
                "ytd": {"actual": "", "budget": "", "var": ""},
            }
        ]
    }
    matrix = {
        "rows": [
            {
                "metric": "Revenue",
                "cm": {"actual": "$999", "budget": "$90", "var": "$10"},
                "qtd": {},
                "ytd": {},
            }
        ]
    }
    # Need full VARIANCE_PERIOD_MATRIX_METRICS coverage — only mismatch on present rows
    # raises; missing other row_ids stay soft.
    soft = verify_variance_commentary_tieout(display, matrix, fail_closed=False)
    assert any(" != " in w for w in soft)
    with pytest.raises(CommentaryIntegrityError, match="fail-closed"):
        verify_variance_commentary_tieout(display, matrix, fail_closed=True)


def test_pptx_script_string_literals_pass_and_invented_hard_blocks() -> None:
    from app.services.commentary.claim_verify import verify_pptx_script_against_evidence

    evidence = {"deck.arr": Decimal("86100000"), "deck.gm": Decimal("79.2")}
    good = 'slide.addText("ARR closed at $86.1M with gross margin 79.2%");'
    assert verify_pptx_script_against_evidence(good, evidence, fail_closed=False).ok

    bad = 'slide.addText("ARR exploded to $99,000,000 this month.");'
    with pytest.raises(CommentaryIntegrityError, match="Prompt 5"):
        verify_pptx_script_against_evidence(bad, evidence, fail_closed=True)


def test_pptx_script_ignores_layout_coords_outside_strings() -> None:
    from app.services.commentary.claim_verify import verify_pptx_script_against_evidence

    evidence = {"deck.arr": Decimal("86100000")}
    # Bare layout numbers must not be treated as customer claims.
    script = "const x = 0.35; const y = 1.25; slide.addText('ARR $86.1M');"
    result = verify_pptx_script_against_evidence(script, evidence, fail_closed=False)
    assert result.ok


def test_apply_fail_closed_to_bullet_list() -> None:
    from app.services.commentary.claim_verify import apply_fail_closed_to_bullet_list

    evidence = {"slide.metrics.arr": Decimal("110000")}
    bullets, result = apply_fail_closed_to_bullet_list(
        [
            "Ending ARR closed at $110,000.",
            "Phantom bookings hit $888,000,000.",
        ],
        evidence,
    )
    assert not result.ok
    assert "110,000" in bullets[0]
    assert bullets[1] == DONT_KNOW_NARRATIVE


def test_evidence_values_from_text_blob_allows_context_numbers() -> None:
    from app.services.commentary.claim_verify import evidence_values_from_text_blob

    blob = "Ending ARR: 86100000\nRevenue was $7,412,000 with GM 79.2%."
    evidence = evidence_values_from_text_blob(blob)
    assert evidence
    ok = verify_text_against_evidence("ARR closed at $86.1M.", evidence)
    assert ok.ok
    bad = verify_text_against_evidence("ARR closed at $99,000,000.", evidence)
    assert not bad.ok

