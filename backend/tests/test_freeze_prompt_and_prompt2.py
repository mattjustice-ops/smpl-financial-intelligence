"""Freeze prompt formatting (shared by Prompt 2 / 5 / regenerate)."""

from __future__ import annotations

from app.services.reporting.export.freeze_prompt import format_freeze_prompt_block


def test_format_freeze_prompt_block_does_not_truncate_by_default() -> None:
    body = "A" * 30000
    block = format_freeze_prompt_block(
        context_text=body,
        context_as_of="2026-07-15T12:00:00+00:00",
        status="COMPLETE",
    )
    assert "CLOSE FREEZE CONTEXT" in block
    assert body in block
    assert "truncated" not in block


def test_format_freeze_prompt_block_stale_label() -> None:
    block = format_freeze_prompt_block(
        context_text="drivers…",
        context_as_of="2026-07-15T12:00:00+00:00",
        status="STALE",
        stale=True,
    )
    assert "STALE" in block
    assert "drivers…" in block
