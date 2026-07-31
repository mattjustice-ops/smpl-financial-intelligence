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


def test_generate_commentary_embeds_evidence_and_keeps_numbers_interactive() -> None:
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
            "narrative": "Ending MRR closed at $110,000 (mrr_waterfall.ending_mrr).",
            "citations": [{"label": "mrr_waterfall.ending_mrr", "value": "$110,000"}],
        },
        "revenue_commentary": {
            "title": "Revenue",
            "narrative": "Invented bookings of $888,000,000.",
            "citations": [],
        },
        "mrr_waterfall_commentary": {
            "title": "MRR",
            "narrative": "NRR of 1.05 on ending MRR $110,000 (mrr_waterfall.ending_mrr).",
            "citations": [{"label": "mrr_waterfall.ending_mrr", "value": "$110,000"}],
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
    # Interactive: unmatched $ soft-warns — section is not replaced with don't-know.
    assert out.revenue_commentary.narrative != DONT_KNOW_NARRATIVE
    assert "888,000,000" in out.revenue_commentary.narrative


def test_interactive_numeric_policy_keeps_text_strict_nukes() -> None:
    from app.services.commentary.claim_verify import fail_closed_text

    evidence = {"ending_mrr": Decimal("110000")}
    text = "Phantom ARR hit $99,000,000."
    bad = verify_text_against_evidence(text, evidence)
    assert not bad.ok
    assert fail_closed_text(text, bad, policy="interactive") == text
    assert fail_closed_text(text, bad, policy="strict") == DONT_KNOW_NARRATIVE


def test_interactive_bullet_list_keeps_unmatched_money() -> None:
    from app.services.commentary.claim_verify import apply_fail_closed_to_bullet_list

    evidence = {"slide.metrics.arr": Decimal("110000")}
    bullets, result = apply_fail_closed_to_bullet_list(
        [
            "Ending ARR closed at $110,000.",
            "Phantom bookings hit $888,000,000.",
        ],
        evidence,
        policy="interactive",
    )
    assert not result.ok
    assert "110,000" in bullets[0]
    assert "888,000,000" in bullets[1]


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
    with pytest.raises(CommentaryIntegrityError, match="failed claim") as exc_info:
        verify_pptx_script_against_evidence(bad, evidence, fail_closed=True)
    assert "$99,000,000" in str(exc_info.value)
    assert "1 failed claim" in str(exc_info.value)


def test_pptx_script_soft_strips_unmatched_money_without_hard_block() -> None:
    from app.services.commentary.claim_verify import (
        PPTX_SOFT_STRIP_CELL,
        apply_fail_closed_claims_to_pptx_script,
    )

    evidence = {"deck.arr": Decimal("86100000")}
    mixed = (
        'slide.addText("ARR closed at $86.1M.");'
        'slide.addText("$99,000,000");'
        'slide.addText("ARR exploded to an unverified $99,000,000 this month vs plan.");'
    )
    rewritten, result = apply_fail_closed_claims_to_pptx_script(mixed, evidence)
    assert not result.ok
    assert "86.1" in rewritten or "86.1M" in rewritten
    assert "$99,000,000" not in rewritten
    assert rewritten.count(f'"{PPTX_SOFT_STRIP_CELL}"') >= 2
    assert "I don't know" not in rewritten
    # Soft-strip path never raises — Prompt 5 export continues.
    assert "failed claim" in result.summary(max_failures=8)


def test_prompt5_verify_soft_strips_and_exports() -> None:
    from app.services.reporting.export.prompt5_deck import _verify_prompt5_script_or_raise

    payload = {
        "period_context": {"close_period": "2026-06"},
        "period_matrix": {"arr": {"actual": 86_100_000}},
        "attribution_package": {
            "allowed_drivers": [
                {"id": "expansion", "label": "Expansion", "aliases": ["expansion"]}
            ]
        },
        "_sources": {
            "deck.arr": {
                "source_type": "WAREHOUSE",
                "table": "arr_waterfall",
                "column": "ending_arr",
                "path": "deck.arr",
            }
        },
    }
    # Invented $ + invented driver soft-stripped; missing cite kept (warn-only).
    script = (
        'slide.addText("ARR closed at $86,100,000 (deck.arr) driven by expansion.");'
        'slide.addText("Cash hit $99,000,000 due to three enterprise upsells.");'
        'slide.addText("$86,100,000");'  # uncited KPI cell — must NOT become don't-know
    )
    out = _verify_prompt5_script_or_raise(script, payload)
    assert isinstance(out, str)
    assert len(out) > 20
    assert "$99,000,000" not in out
    assert "$86,100,000" in out
    assert "verifiable _sources citation" not in out
    assert "I don't know" not in out
    assert 'slide.addText("—")' in out or "slide.addText('—')" in out


def test_deck_evidence_package_includes_forecast_and_pipeline() -> None:
    from app.services.commentary.claim_verify import verify_text_against_evidence
    from app.services.reporting.export.board_platform_metrics import (
        build_evidence_package_from_deck_payload,
    )
    from app.services.reporting.export.prompt5_deck import _verify_prompt5_script_or_raise

    payload = {
        "period_context": {"close_period": "2026-06", "year": "2026", "close_period_label": "June 2026"},
        "monthly_trends": {
            "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
            "ending_arr_m": [80, 81, 82, 83, 84, 86.1, 0, 0],
            "ending_arr_outlook_m": [80, 81, 82, 83, 84, 86.1, 88.2, 90.0],
            "revenue_outlook_m": [6.1, 6.2, 6.3, 6.4, 6.5, 7.4, 7.6, 7.8],
            "pipeline_created_m": [1.1, 1.2, 1.0, 1.3, 1.4, 1.5, 1.6, 1.7],
        },
        "deal_highlights": {
            "top_slipped": [{"name": "Acme Corp", "arr": "$2.4M"}],
            "top_new_customers": [{"name": "Globex", "arr": "$1.1M"}],
        },
        "cash_liquidity": {
            "current_month": {"collections": "$4.2M", "cash_eop_actual": "$12.5M"},
            "bridge_table": {"rows": [{"label": "Collections", "actual": "$4.2M"}]},
        },
        "arr_analysis": {"expansion": "$1.2M", "churn": "$0.4M"},
        "fy_outlook": {"arr_eoy": {"outlook": "$95.0M", "budget": "$100.0M"}},
    }
    pkg = build_evidence_package_from_deck_payload(payload)
    assert pkg["close_period"] == "2026-06"
    values = pkg["values_decimal"]
    # Forecast after close is absolute dollars and verifies.
    assert any(
        abs(v - Decimal("88200000")) <= Decimal("1")
        for k, v in values.items()
        if "2026-07" in k and "ending_arr" in k
    )
    july = verify_text_against_evidence(
        "July ARR outlook is $88.2M (story.forecast.ending_arr_outlook.2026-07).",
        values,
    )
    assert july.ok, july.summary()
    pipe = verify_text_against_evidence(
        "Slipped pipeline includes Acme Corp at $2.4M.",
        values,
    )
    assert pipe.ok, pipe.summary()
    # Sources tagged with series_kind where feasible.
    assert any(
        isinstance(s, dict) and s.get("series_kind") in {"forecast", "pipeline", "actual", "bridge"}
        for s in (pkg.get("_sources") or {}).values()
    )

    # Invented dollars still soft-strip; forecast-in-package keeps; export continues.
    script = (
        'slide.addText("July ARR outlook $88.2M (story.forecast.ending_arr_outlook.2026-07).");'
        'slide.addText("Invented cash spike to $99,000,000.");'
    )
    out = _verify_prompt5_script_or_raise(script, payload)
    assert "$88.2M" in out or "88.2" in out
    assert "$99,000,000" not in out
    assert "I don't know" not in out


def test_to_decimal_parses_variance_plus_and_parens() -> None:
    from app.services.commentary.claim_verify import _to_decimal

    assert _to_decimal("+$1.2M") == Decimal("1200000")
    assert _to_decimal("($0.4M)") == Decimal("-400000")
    assert _to_decimal("—") is None


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


def test_copilot_structured_evidence_package_from_ts_and_waterfalls() -> None:
    from app.services.commentary.claim_verify import (
        build_evidence_package_from_copilot_structures,
        evidence_values_from_package,
        fail_closed_text,
        verify_text_against_evidence,
    )

    ts_data = {
        "Actual": {
            "is": {"2026-06": {"revenue": 7_412_000, "ebitda": -1_297_000}},
            "bs": {"2026-06": {"cash": 70_610_000, "deferred_rev": 1_120_000}},
            "cfs": {"2026-06": {"ending_cash": 70_610_000}},
        }
    }
    cash_bridge = {
        "Actual": {
            "2026-06": {
                "beginning_cash": 66_000_000,
                "collections": 8_000_000,
                "payroll": -3_000_000,
                "ending_cash": 70_610_000,
            }
        }
    }
    bundle = {
        "as_of_period": "2026-06",
        "period_label": "Jun 2026",
        "comparison_waterfalls": {
            "arr": [
                {
                    "waterfall_type": "expansion",
                    "period": "2026-06",
                    "scenario": "Actual",
                    "amount": 2_700_000,
                },
                {
                    "waterfall_type": "ending_arr",
                    "period": "2026-06",
                    "scenario": "Actual",
                    "amount": 86_100_000,
                },
            ]
        },
    }
    pkg = build_evidence_package_from_copilot_structures(
        bundle=bundle,
        ts_data=ts_data,
        cash_bridge_table=cash_bridge,
        focus_period="2026-06",
        period_label="2026-06",
    )
    evidence = evidence_values_from_package(pkg)
    assert any("revenue" in k for k in evidence)
    assert any("ending_arr" in k or "expansion" in k for k in evidence)
    # Structured dotted keys — not only anonymous blob_num
    assert any(k.startswith("ts.") for k in evidence)
    assert any(k.startswith("bundle.") for k in evidence)

    ok = verify_text_against_evidence(
        "Revenue closed at $7,412,000 and ending ARR was $86.1M.",
        evidence,
    )
    assert ok.ok
    bad = verify_text_against_evidence("Revenue closed at $99,000,000.", evidence)
    assert not bad.ok
    assert "don't know" in fail_closed_text("Revenue closed at $99,000,000.", bad).lower()

    # Provenance contract: material keys carry _sources tags
    sources = pkg.get("_sources") or {}
    assert sources
    rev_keys = [k for k in sources if k.endswith(".revenue") or k.endswith("revenue")]
    assert rev_keys
    rev_src = sources[rev_keys[0]]
    assert rev_src.get("source_type") == "WAREHOUSE"
    assert rev_src.get("table") == "income_statement"
    assert rev_src.get("column") == "revenue"
    assert rev_src.get("period") == "2026-06" or rev_src.get("path")


def test_evidence_package_attaches_sources_for_commentary_and_prompt() -> None:
    from app.services.commentary.claim_verify import (
        build_evidence_package,
        evidence_package_for_prompt,
    )

    pkg = build_evidence_package(
        {
            "period_label": "2026-06",
            "mrr_waterfall": {
                "ending_mrr": 7_175_000,
                "expansion_mrr": 225_000,
                "new_mrr": 100_000,
            },
        }
    )
    sources = pkg["_sources"]
    assert "mrr_waterfall.ending_mrr" in sources
    assert sources["mrr_waterfall.ending_mrr"]["source_type"] == "WAREHOUSE"
    assert sources["mrr_waterfall.ending_mrr"]["table"] == "mrr_waterfall"
    assert sources["mrr_waterfall.expansion_mrr"]["column"] == "expansion_mrr"

    prompt_pkg = evidence_package_for_prompt(pkg)
    assert "_sources" in prompt_pkg
    assert prompt_pkg["_sources"]["mrr_waterfall.ending_mrr"]["table"] == "mrr_waterfall"
    assert "Cite" in (prompt_pkg.get("policy") or "")
    for key in ("org_id", "loaded_at", "is_final"):
        assert key in sources["mrr_waterfall.ending_mrr"]

