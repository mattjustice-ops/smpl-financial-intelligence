"""Tests for P15 fail-closed attribution / driver claim verification."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

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
    CustomerMovementSummary,
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
            "narrative": "Ending MRR closed at $110,000 (mrr_waterfall.ending_mrr) driven by three enterprise upsells.",
            "citations": [{"label": "mrr_waterfall.ending_mrr", "value": "$110,000"}],
        },
        "revenue_commentary": {
            "title": "Revenue",
            "narrative": "Revenue commentary deferred.",
            "citations": [],
        },
        "mrr_waterfall_commentary": {
            "title": "MRR",
            "narrative": "Ending MRR was $110,000 (mrr_waterfall.ending_mrr).",
            "citations": [{"label": "mrr_waterfall.ending_mrr", "value": "$110,000"}],
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


def test_deck_payload_builds_bridge_and_matrix_allowlist() -> None:
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_deck_payload,
    )

    pkg = build_attribution_package_from_deck_payload(
        {
            "period_context": {"close_period": "2026-05"},
            "period_matrix": {
                "rows": [
                    {"metric": "Ending ARR"},
                    {"metric": "Revenue"},
                ]
            },
            "arr_analysis": {
                "expansion": "$1.2M",
                "churn": "$0.4M",
                "bridge_table": {
                    "rows": [
                        {"label": "Expansion"},
                        {"label": "Churn"},
                    ]
                },
            },
            "gtm_performance": {
                "channels": [{"channel": "Paid Search"}, {"channel": "Outbound"}]
            },
        }
    )
    ids = {d["id"] for d in pkg["allowed_drivers"]}
    labels = {d["label"].lower() for d in pkg["allowed_drivers"]}
    assert "expansion" in ids or any("expansion" in lab for lab in labels)
    assert "ending_arr" in ids or any("ending arr" in lab for lab in labels)
    assert any("paid search" in lab for lab in labels)


def test_apply_fail_closed_attribution_to_bullet_list() -> None:
    from app.services.commentary.attribution_verify import (
        apply_fail_closed_attribution_to_bullet_list,
    )

    allowlist = [
        AllowedDriver(
            id="expansion",
            label="Expansion",
            aliases=("expansion", "expansion arr"),
        )
    ]
    bullets, result = apply_fail_closed_attribution_to_bullet_list(
        [
            "Net new ARR growth was driven by expansion.",
            "ARR grew due to three enterprise upsells.",
            "Ending ARR closed at $86.1M.",
        ],
        allowlist,
    )
    assert not result.ok
    assert "expansion" in bullets[0].lower()
    assert bullets[1] == DONT_KNOW_ATTRIBUTION
    assert "86.1" in bullets[2]


def test_interactive_attribution_surgical_strip_keeps_good_sentences() -> None:
    from app.services.commentary.attribution_verify import (
        apply_fail_closed_attribution_to_bullet_list,
        fail_closed_attribution_text,
        verify_text_attribution,
    )

    allowlist = [
        AllowedDriver(
            id="expansion",
            label="Expansion",
            aliases=("expansion", "expansion arr"),
        )
    ]
    text = (
        "Ending ARR closed at $86.1M. "
        "Growth was driven by three enterprise upsells. "
        "Expansion remained the largest bridge component."
    )
    result = verify_text_attribution(text, allowlist)
    assert not result.ok
    cleaned = fail_closed_attribution_text(text, result, policy="interactive")
    assert "86.1" in cleaned
    assert "three enterprise upsells" not in cleaned.lower()
    assert cleaned != DONT_KNOW_ATTRIBUTION

    bullets, bres = apply_fail_closed_attribution_to_bullet_list(
        [
            "Ending ARR closed at $86.1M. ARR grew due to three enterprise upsells.",
            "Net new ARR growth was driven by expansion.",
        ],
        allowlist,
        policy="interactive",
    )
    assert not bres.ok
    assert "86.1" in bullets[0]
    assert "three enterprise upsells" not in bullets[0].lower()
    assert "expansion" in bullets[1].lower()


def test_forward_looking_requires_forecast_pipeline_grounding() -> None:
    from app.services.commentary.attribution_verify import (
        DONT_KNOW_FORWARD,
        apply_forward_looking_policy_to_text,
        verify_text_forward_looking,
    )

    allowlist = [
        AllowedDriver(
            id="expansion",
            label="Expansion",
            source="comparison_waterfalls.arr.expansion",
            aliases=("expansion",),
        ),
        AllowedDriver(
            id="pipeline_coverage",
            label="Pipeline coverage",
            source="pipeline_changes.coverage",
            aliases=("pipeline coverage", "coverage"),
        ),
    ]
    invented = "Watch out for logo-loss churn next quarter."
    bad = verify_text_forward_looking(invented, allowlist)
    assert not bad.ok
    stripped, _ = apply_forward_looking_policy_to_text(
        invented, allowlist, policy="interactive"
    )
    assert stripped == DONT_KNOW_FORWARD

    grounded = (
        "Ending ARR closed at $86.1M. "
        "Watch out for pipeline coverage pressure next quarter."
    )
    ok = verify_text_forward_looking(grounded, allowlist)
    assert ok.ok
    kept, _ = apply_forward_looking_policy_to_text(
        grounded, allowlist, policy="interactive"
    )
    assert "86.1" in kept
    assert "pipeline coverage" in kept.lower()


def test_pptx_script_attribution_soft_strips_and_hard_blocks_when_fully_wiped() -> None:
    from app.services.commentary.attribution_verify import (
        apply_fail_closed_attribution_to_pptx_script,
        raise_if_pptx_attribution_fully_unverifiable,
    )
    from app.services.commentary.claim_verify import CommentaryIntegrityError

    allowlist = [
        AllowedDriver(
            id="expansion",
            label="Expansion",
            aliases=("expansion",),
        )
    ]
    mixed = (
        'slide.addText("ARR growth was driven by expansion.");'
        'slide.addText("Growth was due to three enterprise upsells.");'
    )
    rewritten, result = apply_fail_closed_attribution_to_pptx_script(mixed, allowlist)
    assert not result.ok
    assert "expansion" in rewritten.lower()
    assert DONT_KNOW_ATTRIBUTION[:40] in rewritten
    # Partial wipe → do not hard-block
    raise_if_pptx_attribution_fully_unverifiable(result)

    bad_only = 'slide.addText("ARR grew due to three enterprise upsells.");'
    wiped, bad_result = apply_fail_closed_attribution_to_pptx_script(bad_only, allowlist)
    assert not bad_result.ok
    assert all(c.status != "pass" for c in bad_result.checks)
    assert DONT_KNOW_ATTRIBUTION[:40] in wiped
    with pytest.raises(CommentaryIntegrityError, match="Prompt 5"):
        raise_if_pptx_attribution_fully_unverifiable(bad_result)


def test_copilot_blob_allowlist_is_thin_but_catches_invented_drivers() -> None:
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_text_blob,
        fail_closed_attribution_text,
        verify_text_attribution,
    )

    blob = (
        "ARR bridge: beginning_arr, expansion, churn, ending_arr.\n"
        "Cash bridge: collections, payroll, ending cash."
    )
    pkg = build_attribution_package_from_text_blob(blob)
    ids = {d["id"] for d in pkg["allowed_drivers"]}
    assert "expansion" in ids
    assert "payroll" in ids

    ok = verify_text_attribution("ARR growth was driven by expansion.", pkg)
    assert ok.ok
    bad = verify_text_attribution(
        "ARR growth was driven by three enterprise upsells.", pkg
    )
    assert not bad.ok
    assert fail_closed_attribution_text(
        "ARR growth was driven by three enterprise upsells.", bad
    ) == DONT_KNOW_ATTRIBUTION


def test_deal_count_and_named_logo_drivers_from_commentary_inputs() -> None:
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_commentary_inputs,
        verify_text_attribution,
    )
    from app.services.commentary.schemas import CustomerMovementSummary

    inputs = CommentaryInputs(
        period_label="Jun 2026",
        mrr_waterfall=MrrWaterfallSummary(
            period=date(2026, 6, 1),
            beginning_mrr=Decimal("7000000"),
            new_mrr=Decimal("100000"),
            expansion_mrr=Decimal("2700000"),
            contraction_mrr=Decimal("-50000"),
            churn_mrr=Decimal("-400000"),
            reactivation_mrr=Decimal("0"),
            ending_mrr=Decimal("9350000"),
        ),
        customer_movement=CustomerMovementSummary(
            new_customers=3,
            churned_customers=1,
            expanded_customers=2,
            contracted_customers=0,
            reactivated_customers=0,
            notable_customers=["Acme Corp", "Globex"],
        ),
    )
    pkg = build_attribution_package_from_commentary_inputs(inputs)
    labels = " ".join(
        " ".join([d["label"], *(d.get("aliases") or [])]) for d in pkg["allowed_drivers"]
    ).lower()
    assert "three new customers" in labels or "3 new customers" in labels
    assert "acme corp" in labels
    assert "globex" in labels

    ok = verify_text_attribution(
        "Logo growth was driven by three new customers and Acme Corp.",
        pkg,
    )
    assert ok.ok
    # Invented deal story still fail-closed
    bad = verify_text_attribution(
        "ARR growth was driven by three enterprise upsells.",
        pkg,
    )
    assert not bad.ok


def test_magnitude_dominance_aliases_on_arr_bridge() -> None:
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_copilot_structures,
        verify_text_attribution,
    )

    bundle = {
        "as_of_period": "2026-06",
        "comparison_waterfalls": {
            "arr": [
                {
                    "waterfall_type": "expansion",
                    "period": "2026-06",
                    "amount": 2_700_000,
                },
                {
                    "waterfall_type": "churn",
                    "period": "2026-06",
                    "amount": -400_000,
                },
                {
                    "waterfall_type": "new_business",
                    "period": "2026-06",
                    "amount": 200_000,
                },
            ]
        },
        "opportunity_attribution": [
            {
                "customer_name": "Initech",
                "opportunity_name": "Initech Upsell",
                "movement_type": "expansion",
                "amount": 900_000,
            },
            {
                "customer_name": "Umbrella",
                "movement_type": "expansion",
                "amount": 800_000,
            },
            {
                "customer_name": "Stark",
                "movement_type": "expansion",
                "amount": 700_000,
            },
        ],
    }
    pkg = build_attribution_package_from_copilot_structures(
        bundle=bundle, focus_period="2026-06"
    )
    expansion = next(d for d in pkg["allowed_drivers"] if d["id"] == "expansion")
    aliases = " ".join(expansion.get("aliases") or []).lower()
    assert "primarily expansion" in aliases or "largest bridge component" in aliases

    ok = verify_text_attribution(
        "ARR movement was driven by the largest bridge component.",
        pkg,
    )
    assert ok.ok

    logo_blob = " ".join(
        " ".join([d["label"], *(d.get("aliases") or [])]) for d in pkg["allowed_drivers"]
    ).lower()
    assert "initech" in logo_blob
    assert "three expansion deals" in logo_blob or "3 expansion deals" in logo_blob


def test_copilot_structured_attribution_from_waterfalls_and_cash_bridge() -> None:
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_copilot_structures,
        fail_closed_attribution_text,
        verify_text_attribution,
    )

    bundle = {
        "as_of_period": "2026-06",
        "comparison_waterfalls": {
            "arr": [
                {
                    "waterfall_type": "expansion",
                    "period": "2026-06",
                    "scenario": "Actual",
                    "amount": 2_700_000,
                },
                {
                    "waterfall_type": "churn",
                    "period": "2026-06",
                    "scenario": "Actual",
                    "amount": -400_000,
                },
            ]
        },
    }
    cash_bridge = {
        "Actual": {
            "2026-06": {
                "collections": 8_000_000,
                "payroll": -3_000_000,
            }
        }
    }
    pkg = build_attribution_package_from_copilot_structures(
        bundle=bundle,
        cash_bridge_table=cash_bridge,
        focus_period="2026-06",
    )
    ids = {d["id"] for d in pkg["allowed_drivers"]}
    assert "expansion" in ids
    assert "churn" in ids
    assert "payroll" in ids or "collections" in ids
    # Structured source — not only context_blob_label
    sources = {d.get("source") or "" for d in pkg["allowed_drivers"]}
    assert any(s.startswith("comparison_waterfalls") for s in sources)
    assert any(s.startswith("cash_bridge") for s in sources)

    ok = verify_text_attribution("ARR growth was driven by expansion.", pkg)
    assert ok.ok
    bad = verify_text_attribution(
        "ARR growth was driven by three enterprise upsells.", pkg
    )
    assert not bad.ok
    assert (
        fail_closed_attribution_text(
            "ARR growth was driven by three enterprise upsells.", bad
        )
        == DONT_KNOW_ATTRIBUTION
    )

def test_multi_driver_and_phrase_requires_all_allowlisted() -> None:
    """Comma/'and' lists fail closed unless EVERY named driver is allowlisted."""
    allowlist = [
        AllowedDriver(
            id="expansion_mrr",
            label="Expansion MRR",
            aliases=("expansion", "expansion mrr"),
        ),
        AllowedDriver(
            id="churn_mrr",
            label="Churn MRR",
            aliases=("churn", "churn mrr"),
        ),
    ]
    both_ok = verify_text_attribution(
        "Net new was driven by expansion and churn.",
        allowlist,
    )
    assert both_ok.ok
    assert both_ok.checks[0].matched_driver_id
    assert "expansion" in (both_ok.checks[0].matched_driver_id or "")
    assert "churn" in (both_ok.checks[0].matched_driver_id or "")

    oxford = verify_text_attribution(
        "Movement was driven by expansion, contraction, and churn.",
        allowlist,
    )
    assert not oxford.ok
    assert any(c.status == "partial_allowlist" for c in oxford.failures)

    mixed = verify_text_attribution(
        "ARR growth was driven by expansion and three enterprise upsells.",
        allowlist,
    )
    assert not mixed.ok
    assert any(c.status == "partial_allowlist" for c in mixed.failures)
    assert fail_closed_attribution_text(
        "ARR growth was driven by expansion and three enterprise upsells.",
        mixed,
    ) == DONT_KNOW_ATTRIBUTION

