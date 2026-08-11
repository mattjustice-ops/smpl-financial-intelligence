"""Clarify-before-write fragments are embedded on primary AI surfaces."""

from __future__ import annotations

from app.services.commentary.clarify_before_write import (
    CLARIFY_BEFORE_WRITE_EXPORT,
    CLARIFY_BEFORE_WRITE_INTERACTIVE,
)
from app.services.commentary.prompts import SYSTEM_PROMPT
from app.services.reporting.export.board_api_prompts import BOARD_DECK_SLIDE_SYSTEM_PROMPT
from app.services.reporting.export.prompt2_system import PROMPT2_SYSTEM
from app.services.reporting.export.prompt5_narrative import PROMPT5_CRAFT_CRITERIA


def test_export_fragment_requires_preflight_not_invention() -> None:
    text = CLARIFY_BEFORE_WRITE_EXPORT
    assert "CLARIFY / PLAN BEFORE WRITE" in text
    assert "close date" in text.lower() or "start" in text.lower()
    assert "insufficient-evidence" in text.lower() or "don't-know" in text.lower()
    assert "never invent" in text.lower() or "never fabricate" in text.lower()


def test_interactive_fragment_asks_when_underspecified() -> None:
    text = CLARIFY_BEFORE_WRITE_INTERACTIVE
    assert "CLARIFY BEFORE ANSWERING" in text
    assert "clarifying questions" in text.lower()
    assert "close date" in text.lower() or "start date" in text.lower()


def test_fragments_embedded_in_primary_prompts() -> None:
    assert "CLARIFY / PLAN BEFORE WRITE" in PROMPT2_SYSTEM
    assert "CLARIFY / PLAN BEFORE WRITE" in PROMPT5_CRAFT_CRITERIA
    assert "CLARIFY / PLAN BEFORE WRITE" in BOARD_DECK_SLIDE_SYSTEM_PROMPT
    assert "CLARIFY / PLAN BEFORE WRITE" in SYSTEM_PROMPT
