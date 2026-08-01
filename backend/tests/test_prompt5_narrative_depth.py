"""Prompt 5 board-narrative depth instructions (regenerate/Copilot shape)."""

from __future__ import annotations

from unittest.mock import patch

from app.services.reporting.export.board_platform_ro_seed import (
    BOARD_PLATFORM_RISKS_OPPORTUNITIES,
    BOARD_RO_SEED_MARKER,
    GTM_NARRATIVE_SEED_MARKER,
    board_ro_cards_for_payload,
    format_board_ro_seed_block,
    format_gtm_narrative_requirements_block,
)
from app.services.reporting.export.prompt5_adapt import PROMPT5_ADAPT_SYSTEM
from app.services.reporting.export.prompt5_deck import (
    PROMPT5_SYSTEM,
    _build_fix_prompt,
    _excerpt_for_prompt,
    build_prompt5_package_preamble,
    build_prompt5_user_message,
)
from app.services.reporting.export.prompt5_narrative import PROMPT5_BOARD_NARRATIVE_RULES


def test_prompt5_narrative_rules_require_insight_shape_not_delta_stubs() -> None:
    text = PROMPT5_BOARD_NARRATIVE_RULES
    assert "PRIMARY DRIVER + VARIANCE CONTEXT" in text
    assert "RETENTION / PIPELINE QUALITY" in text
    assert "RECOMMENDED BOARD ACTION" in text
    assert "3–5 insight bullets" in text or "3-5 insight bullets" in text
    assert "~28–45 words" in text or "28–45 words" in text
    assert "Actual" in text and "Forecast" in text and "Pipeline" in text
    # KPI cells stay numbers; citations only in takeaways.
    assert "KPI / TABLE CELLS" in text
    assert 'numbers (or "—") ONLY' in text
    assert "don't-know essays" in text
    assert "BOARD R&O SEED" in text or "RISKS / OPPORTUNITIES CARDS" in text
    assert "closed-lost" in text.lower() or "CLOSED-LOST" in text


def test_prompt5_v3_and_adapt_systems_embed_narrative_rules() -> None:
    assert "PRIMARY DRIVER + VARIANCE CONTEXT" in PROMPT5_SYSTEM
    assert "BOARD NARRATIVE DEPTH" in PROMPT5_SYSTEM
    assert "KPI / TABLE CELLS" in PROMPT5_SYSTEM
    assert "PRIMARY DRIVER + VARIANCE CONTEXT" in PROMPT5_ADAPT_SYSTEM
    assert "REWRITE all narrative text" in PROMPT5_ADAPT_SYSTEM or "REWRITE" in PROMPT5_ADAPT_SYSTEM
    assert "BOARD R&O SEED" in PROMPT5_ADAPT_SYSTEM
    assert "closed-lost" in PROMPT5_ADAPT_SYSTEM.lower()
    # Old thin stub cap must not remain as the governing instruction.
    assert "max 22 words" not in PROMPT5_SYSTEM
    assert "max 22 words" not in PROMPT5_ADAPT_SYSTEM


def test_board_ro_seed_matches_board_platform_tab_cards() -> None:
    cards = BOARD_PLATFORM_RISKS_OPPORTUNITIES
    assert len(cards["risks"]) == 4
    assert len(cards["opportunities"]) == 4
    titles = {c["title"] for c in cards["risks"]} | {c["title"] for c in cards["opportunities"]}
    assert "Paid channel inefficiency" in titles
    assert "SMB churn concentration" in titles
    assert "New logo $325k behind plan" in titles
    assert "H2 collections moderation" in titles
    assert "Partner + Referral reallocation" in titles
    assert "Expansion ARR momentum" in titles
    assert "Annual contract expansion" in titles
    assert "Operating leverage improvement" in titles
    payload = board_ro_cards_for_payload()
    assert all(c.get("detail") and c.get("action") for c in payload["risks"])
    assert all(c.get("detail") and c.get("action") for c in payload["opportunities"])
    seed = format_board_ro_seed_block()
    assert BOARD_RO_SEED_MARKER in seed
    assert "Paid channel inefficiency" in seed
    assert "MUST" in seed
    gtm = format_gtm_narrative_requirements_block()
    assert GTM_NARRATIVE_SEED_MARKER in gtm
    assert "closed-lost" in gtm.lower()
    assert "slipped" in gtm.lower()
    assert "coverage" in gtm.lower()
    assert "recommended board action" in gtm.lower()


def test_prompt5_preamble_and_user_message_inject_ro_and_gtm_seeds() -> None:
    fake_payload = {
        "period_context": {
            "close_period": "2026-06",
            "close_period_label": "June 2026",
            "quarter": "Q2 2026",
            "ytd_label": "YTD Jun 2026",
            "output_filename": "mda_deck_2026-06.pptx",
        },
        "payload_warnings": [],
        "monthly_trends": {
            "months": ["Jun", "Jul"],
            "ending_arr_outlook_m": [86.1, 88.2],
        },
        "risks_and_opportunities": board_ro_cards_for_payload(),
        "gtm_performance": {
            "closed_lost_raw": 7_910_000,
            "slipped_pipeline_raw": 9_870_000,
            "narrative_must_cover": ["closed_lost actual vs budget + variance"],
        },
    }
    preamble = build_prompt5_package_preamble(fake_payload)
    assert BOARD_RO_SEED_MARKER in preamble
    assert GTM_NARRATIVE_SEED_MARKER in preamble
    assert "Paid channel inefficiency" in preamble
    assert "SMB churn concentration" in preamble
    assert "closed-lost" in preamble.lower()

    with patch(
        "app.services.reporting.export.prompt5_deck.build_prompt5_payload",
        return_value=fake_payload,
    ):
        msg = build_prompt5_user_message(
            object(),  # type: ignore[arg-type]
            freeze_context_text="Expansion drove ARR; slipped pipeline Acme $2.4M.",
            freeze_context_as_of="2026-07-14T12:00:00+00:00",
            freeze_status="CURRENT",
            freeze_stale=False,
        )
    assert "TAKEAWAY / COMMENTARY SHAPE" in msg
    assert "PRIMARY DRIVER + VARIANCE" in msg
    assert "RETENTION/PIPELINE QUALITY" in msg or "RETENTION / PIPELINE QUALITY" in msg
    assert "RECOMMENDED BOARD ACTION" in msg
    assert "CLOSE FREEZE CONTEXT" in msg
    assert "Expansion drove ARR" in msg
    assert "EVIDENCE PACKAGE" in msg
    assert "ATTRIBUTION PACKAGE" in msg
    assert BOARD_RO_SEED_MARKER in msg
    assert GTM_NARRATIVE_SEED_MARKER in msg
    assert "BOARD R&O SEED" in msg
    assert "GTM NARRATIVE REQUIREMENTS" in msg
    assert "KEY TAKEAWAYS SEED" in msg
    assert "KPI/table cells" in msg.lower() or "KPI/table" in msg
    assert "rich board narrative" in msg.lower() or "board-ready" in msg.lower()


def test_prompt5_user_message_injects_narrative_shape_and_freeze() -> None:
    fake_payload = {
        "period_context": {
            "close_period": "2026-06",
            "close_period_label": "June 2026",
            "quarter": "Q2 2026",
            "ytd_label": "YTD Jun 2026",
            "output_filename": "mda_deck_2026-06.pptx",
        },
        "payload_warnings": [],
        "monthly_trends": {
            "months": ["Jun", "Jul"],
            "ending_arr_outlook_m": [86.1, 88.2],
        },
    }
    with patch(
        "app.services.reporting.export.prompt5_deck.build_prompt5_payload",
        return_value=fake_payload,
    ):
        msg = build_prompt5_user_message(
            object(),  # type: ignore[arg-type]
            freeze_context_text="Expansion drove ARR; slipped pipeline Acme $2.4M.",
            freeze_context_as_of="2026-07-14T12:00:00+00:00",
            freeze_status="CURRENT",
            freeze_stale=False,
        )
    assert "TAKEAWAY / COMMENTARY SHAPE" in msg
    assert "PRIMARY DRIVER + VARIANCE" in msg
    assert "RETENTION/PIPELINE QUALITY" in msg or "RETENTION / PIPELINE QUALITY" in msg
    assert "RECOMMENDED BOARD ACTION" in msg
    assert "CLOSE FREEZE CONTEXT" in msg
    assert "Expansion drove ARR" in msg
    assert "EVIDENCE PACKAGE" in msg
    assert "ATTRIBUTION PACKAGE" in msg
    assert BOARD_RO_SEED_MARKER in msg
    assert GTM_NARRATIVE_SEED_MARKER in msg
    assert "KPI/table cells" in msg.lower() or "KPI/table" in msg
    assert "rich board narrative" in msg.lower() or "board-ready" in msg.lower()


def test_excerpt_for_prompt_truncates_and_is_callable_from_fix() -> None:
    """Adapt/fix prompts must resolve _excerpt_for_prompt (NameError regression)."""
    short = "abc"
    assert _excerpt_for_prompt(short, limit=10) == short
    long = "x" * 100
    out = _excerpt_for_prompt(long, limit=20)
    assert len(out) < len(long)
    assert "middle omitted" in out
    fix = _build_fix_prompt(
        last_error="boom",
        failed_script="const pptx = new PptxGenJS();",
        payload_json='{"period":"2026-06"}',
    )
    assert "FAILED SCRIPT:" in fix
    assert "DATA PAYLOAD" in fix
