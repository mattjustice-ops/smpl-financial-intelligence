"""Prompt 5 freeze context is injected into the Claude user message."""

from __future__ import annotations

from unittest.mock import patch

from app.services.reporting.export.prompt5_deck import build_prompt5_user_message


def test_prompt5_user_message_includes_freeze_context_and_stale_label() -> None:
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
    bundle = object()  # unused because payload is mocked
    with patch(
        "app.services.reporting.export.prompt5_deck.build_prompt5_payload",
        return_value=fake_payload,
    ):
        msg = build_prompt5_user_message(
            bundle,  # type: ignore[arg-type]
            freeze_context_text="ARR section from freeze pack…",
            freeze_context_as_of="2026-07-14T12:00:00+00:00",
            freeze_status="STALE",
            freeze_stale=True,
        )
    assert "CLOSE FREEZE CONTEXT" in msg
    assert "Context source: freeze" in msg
    assert "STALE" in msg
    assert "2026-07-14T12:00:00+00:00" in msg
    assert "ARR section from freeze pack…" in msg
    assert "DATA PAYLOAD (JSON):" in msg
    assert "EVIDENCE PACKAGE" in msg
    assert "Actuals: periods ≤" in msg
    assert "Forecast / outlook" in msg
    assert "rich board narrative" in msg.lower() or "Rich narrative" in msg


def test_prompt5_user_message_omits_freeze_block_when_absent() -> None:
    fake_payload = {
        "period_context": {
            "close_period": "2026-06",
            "close_period_label": "June 2026",
            "quarter": "Q2 2026",
            "ytd_label": "YTD Jun 2026",
            "output_filename": "mda_deck_2026-06.pptx",
        },
        "payload_warnings": [],
    }
    with patch(
        "app.services.reporting.export.prompt5_deck.build_prompt5_payload",
        return_value=fake_payload,
    ):
        msg = build_prompt5_user_message(object())  # type: ignore[arg-type]
    assert "CLOSE FREEZE CONTEXT" not in msg
    assert "DATA PAYLOAD (JSON):" in msg
    assert "EVIDENCE PACKAGE" in msg
    assert "series_kinds" in msg
