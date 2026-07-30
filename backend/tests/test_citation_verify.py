"""Tests for P15 fail-closed citation verify against _sources."""

from __future__ import annotations

from app.services.commentary.citation_verify import (
    DONT_KNOW_CITATION,
    apply_fail_closed_citations_to_commentary,
    fail_closed_citation_text,
    verify_text_citations,
)
from app.services.commentary.claim_verify import build_evidence_package
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
