"""Tests for P15 fail-closed citation verify against _sources."""

from __future__ import annotations

import pytest

from app.services.commentary.citation_verify import (
    DONT_KNOW_CITATION,
    apply_fail_closed_citations_to_bullet_list,
    apply_fail_closed_citations_to_commentary,
    apply_fail_closed_citations_to_pptx_script,
    fail_closed_citation_text,
    raise_if_pptx_citation_fully_unverifiable,
    verify_text_citations,
)
from app.services.commentary.claim_verify import (
    CommentaryIntegrityError,
    build_evidence_package,
)
from app.services.commentary.schemas import CommentaryOutput, CommentarySection


def test_inline_and_structured_citations_pass() -> None:
    sources = {
        "mrr_waterfall.ending_mrr": {
            "source_type": "WAREHOUSE",
            "table": "mrr_waterfall",
            "column": "ending_mrr",
            "path": "mrr_waterfall.ending_mrr",
            "value": "110000",
            "org_id": None,
            "loaded_at": None,
            "is_final": None,
        }
    }
    ok = verify_text_citations(
        "Ending MRR closed at $110,000 (mrr_waterfall.ending_mrr).",
        sources,
    )
    assert ok.ok
    ok2 = verify_text_citations(
        "Ending MRR closed at $110,000 (mrr_waterfall.ending_mrr, period 2026-06).",
        sources,
    )
    assert ok2.ok
    missing = verify_text_citations("Ending MRR closed at $110,000.", sources)
    assert not missing.ok
    assert any(c.status == "missing_citation" for c in missing.failures)
    assert (
        fail_closed_citation_text("Ending MRR closed at $110,000.", missing)
        == DONT_KNOW_CITATION
    )

    output = CommentaryOutput(
        period_label="May 2026",
        executive_summary=CommentarySection(
            title="Exec",
            narrative="Ending MRR closed at $110,000.",
            citations=[{"label": "mrr_waterfall.ending_mrr", "value": "$110,000"}],
        ),
        revenue_commentary=CommentarySection(
            title="Rev", narrative="No figures stated.", citations=[]
        ),
        mrr_waterfall_commentary=CommentarySection(
            title="MRR", narrative="No figures stated.", citations=[]
        ),
        bookings_forecast_commentary=CommentarySection(
            title="Bookings", narrative="No figures stated.", citations=[]
        ),
        cash_forecast_commentary=CommentarySection(
            title="Cash", narrative="No figures stated.", citations=[]
        ),
    )
    verified, result = apply_fail_closed_citations_to_commentary(output, sources)
    assert result.ok
    assert "110,000" in verified.executive_summary.narrative


def test_pptx_script_citation_soft_strips_and_hard_blocks_when_fully_wiped() -> None:
    sources = {
        "income_statement.revenue": {
            "source_type": "WAREHOUSE",
            "table": "income_statement",
            "column": "revenue",
            "path": "deck.period_matrix.revenue",
        }
    }
    mixed = (
        'slide.addText("Revenue closed at $7,400,000 (income_statement.revenue).");'
        'slide.addText("Cash ended at $70,000,000.");'
    )
    rewritten, result = apply_fail_closed_citations_to_pptx_script(mixed, sources)
    assert not result.ok
    assert "income_statement.revenue" in rewritten
    assert DONT_KNOW_CITATION[:40] in rewritten
    # Partial wipe → do not hard-block
    raise_if_pptx_citation_fully_unverifiable(result)

    bad_only = 'slide.addText("Cash ended at $70,000,000.");'
    wiped, bad_result = apply_fail_closed_citations_to_pptx_script(bad_only, sources)
    assert not bad_result.ok
    assert all(c.status != "pass" for c in bad_result.checks)
    assert DONT_KNOW_CITATION[:40] in wiped
    with pytest.raises(CommentaryIntegrityError, match="Prompt 5"):
        raise_if_pptx_citation_fully_unverifiable(bad_result)


def test_bullet_list_citation_soft_strip() -> None:
    sources = {
        "arr_waterfall.ending_arr": {
            "source_type": "WAREHOUSE",
            "table": "arr_waterfall",
            "column": "ending_arr",
            "path": "arr_waterfall.ending_arr",
        }
    }
    bullets = [
        "Ending ARR closed at $86,100,000 (arr_waterfall.ending_arr).",
        "Revenue hit $7,400,000.",
    ]
    cleaned, result = apply_fail_closed_citations_to_bullet_list(bullets, sources)
    assert not result.ok
    assert "arr_waterfall.ending_arr" in cleaned[0]
    assert cleaned[1] == DONT_KNOW_CITATION


def test_interactive_citation_policy_keeps_uncited_money() -> None:
    sources = {
        "arr_waterfall.ending_arr": {
            "source_type": "WAREHOUSE",
            "table": "arr_waterfall",
            "column": "ending_arr",
            "path": "arr_waterfall.ending_arr",
        }
    }
    text = "Revenue hit $7,400,000."
    missing = verify_text_citations(text, sources)
    assert not missing.ok
    assert fail_closed_citation_text(text, missing, policy="interactive") == text
    assert fail_closed_citation_text(text, missing, policy="strict") == DONT_KNOW_CITATION

    bullets = [
        "Ending ARR closed at $86,100,000 (arr_waterfall.ending_arr).",
        "Revenue hit $7,400,000.",
    ]
    cleaned, result = apply_fail_closed_citations_to_bullet_list(
        bullets, sources, policy="interactive"
    )
    assert not result.ok
    assert "7,400,000" in cleaned[1]


def test_warehouse_tags_on_sources_honest_nulls_and_populated() -> None:
    pkg = build_evidence_package(
        {
            "period_label": "2026-06",
            "mrr_waterfall": {"ending_mrr": 7_175_000},
        }
    )
    src = pkg["_sources"]["mrr_waterfall.ending_mrr"]
    for key in ("org_id", "loaded_at", "is_final"):
        assert key in src
        assert src[key] is None

    tagged = build_evidence_package(
        {
            "period_label": "2026-06",
            "org_id": "org-123",
            "loaded_at": "2026-07-05T14:23:11Z",
            "is_final": True,
            "mrr_waterfall": {"ending_mrr": 7_175_000},
        }
    )
    src2 = tagged["_sources"]["mrr_waterfall.ending_mrr"]
    assert src2["org_id"] == "org-123"
    assert src2["loaded_at"] == "2026-07-05T14:23:11Z"
    assert src2["is_final"] is True
