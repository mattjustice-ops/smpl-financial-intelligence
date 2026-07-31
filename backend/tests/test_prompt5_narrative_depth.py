"""Prompt 5 board-narrative depth instructions (regenerate/Copilot shape)."""

from __future__ import annotations

from unittest.mock import patch

from app.services.reporting.export.prompt5_adapt import PROMPT5_ADAPT_SYSTEM
from app.services.reporting.export.prompt5_deck import (
    PROMPT5_SYSTEM,
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


def test_prompt5_v3_and_adapt_systems_embed_narrative_rules() -> None:
    assert "PRIMARY DRIVER + VARIANCE CONTEXT" in PROMPT5_SYSTEM
    assert "BOARD NARRATIVE DEPTH" in PROMPT5_SYSTEM
    assert "KPI / TABLE CELLS" in PROMPT5_SYSTEM
    assert "PRIMARY DRIVER + VARIANCE CONTEXT" in PROMPT5_ADAPT_SYSTEM
    assert "REWRITE all narrative text" in PROMPT5_ADAPT_SYSTEM or "REWRITE" in PROMPT5_ADAPT_SYSTEM
    # Old thin stub cap must not remain as the governing instruction.
    assert "max 22 words" not in PROMPT5_SYSTEM
    assert "max 22 words" not in PROMPT5_ADAPT_SYSTEM


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
    assert "KPI/table cells" in msg.lower() or "KPI/table" in msg
    assert "rich board narrative" in msg.lower() or "board-ready" in msg.lower()
