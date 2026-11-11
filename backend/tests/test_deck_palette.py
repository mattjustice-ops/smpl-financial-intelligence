"""Company deck colors stay on the shipped palette until a color is stored."""

from __future__ import annotations

import uuid

import pytest

from app.services.reporting.deck_palette import (
    DECK_PALETTE_DEFAULTS,
    DeckPaletteRejected,
    company_deck_record,
    effective_palette,
    merge_palette,
)


def test_empty_palette_is_the_shipped_deck() -> None:
    colors = effective_palette(None)
    assert colors == DECK_PALETTE_DEFAULTS
    record = company_deck_record(
        organization_id=uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f"),
        close_month="2026-06",
        fiscal_year_end_month=12,
        palette_raw=None,
        template_filename=None,
    )
    assert record["presentation"] == "ours"
    assert record["palette_custom"] is False
    assert record["palette_stored"] == {}
    assert record["palette"]["accent"] == "#00D4AA"
    assert record["template_filename"] is None


def test_one_color_keeps_the_other_shipped_colors() -> None:
    stored = merge_palette(None, {"accent": "#e0a100"}, reset=False)
    colors = effective_palette(stored)
    assert stored == {"accent": "E0A100"}
    assert colors["accent"] == "E0A100"
    assert colors["background"] == DECK_PALETTE_DEFAULTS["background"]
    assert colors["favorable"] == "22C55E"


def test_clearing_a_color_returns_it_to_the_shipped_deck() -> None:
    stored = merge_palette({"accent": "E0A100", "card": "2C2150"}, {"accent": None}, reset=False)
    assert stored == {"card": "2C2150"}
    assert effective_palette(stored)["accent"] == DECK_PALETTE_DEFAULTS["accent"]


def test_reset_clears_the_stored_palette() -> None:
    assert merge_palette({"accent": "E0A100"}, {}, reset=True) is None


def test_a_bad_color_is_refused() -> None:
    with pytest.raises(DeckPaletteRejected, match="Accent"):
        merge_palette(None, {"accent": "teal"}, reset=False)


def test_an_unknown_color_is_refused() -> None:
    with pytest.raises(DeckPaletteRejected, match="not on the company record"):
        merge_palette(None, {"logo": "#000000"}, reset=False)


def test_a_stored_presentation_is_theirs() -> None:
    record = company_deck_record(
        organization_id=uuid.uuid4(),
        close_month=None,
        fiscal_year_end_month=6,
        palette_raw={"muted": "445566"},
        template_filename="Board.pptx",
    )
    assert record["presentation"] == "company"
    assert record["template_filename"] == "Board.pptx"
    assert record["fiscal_year_end_month"] == 6
    assert record["palette_custom"] is True
    assert record["palette"]["muted"] == "#445566"
