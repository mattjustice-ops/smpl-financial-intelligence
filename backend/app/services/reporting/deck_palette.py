"""Colors stored on the company for our board deck.

An empty palette means the colors shipped with the template. A company that
later sends its own presentation is recorded separately, on the slide-deck
template. This record does not map their text boxes.
"""

from __future__ import annotations

import re
import uuid

_HEX = re.compile(r"^[0-9A-F]{6}$")

DECK_PALETTE_DEFAULTS: dict[str, str] = {
    "background": "070D18",
    "card": "111D2E",
    "accent": "00D4AA",
    "muted": "6B8CA8",
    "favorable": "22C55E",
    "unfavorable": "EF4444",
}

_LABELS = {
    "background": "Background",
    "card": "Card",
    "accent": "Accent",
    "muted": "Muted text",
    "favorable": "Favorable",
    "unfavorable": "Unfavorable",
}


class DeckPaletteRejected(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _display(value: str) -> str:
    return f"#{value}"


def normalize_deck_color(key: str, value: object) -> str:
    label = _LABELS.get(key, "Color")
    if not isinstance(value, str):
        raise DeckPaletteRejected(f"{label} needs six hex digits, like #00D4AA.")
    text = value.strip().upper()
    if text.startswith("#"):
        text = text[1:]
    if not _HEX.fullmatch(text):
        raise DeckPaletteRejected(f"{label} needs six hex digits, like #00D4AA.")
    return text


def stored_palette(raw: object) -> dict[str, str]:
    """Colors this company has set. Unknown or blank entries are left out."""
    if not isinstance(raw, dict):
        return {}
    kept: dict[str, str] = {}
    for key, value in raw.items():
        if key not in DECK_PALETTE_DEFAULTS or not isinstance(value, str):
            continue
        try:
            kept[key] = normalize_deck_color(key, value)
        except DeckPaletteRejected:
            continue
    return kept


def effective_palette(raw: object) -> dict[str, str]:
    """The six colors the deck will use. Unset keys stay on the shipped colors."""
    colors = dict(DECK_PALETTE_DEFAULTS)
    colors.update(stored_palette(raw))
    return colors


def merge_palette(raw: object, updates: dict[str, str | None], *, reset: bool) -> dict[str, str] | None:
    """Return the palette to store. None means the company is on the shipped colors."""
    current: dict[str, str] = {} if reset else stored_palette(raw)
    for key, value in updates.items():
        if key not in DECK_PALETTE_DEFAULTS:
            raise DeckPaletteRejected("That color is not on the company record.")
        if value is None or (isinstance(value, str) and not value.strip()):
            current.pop(key, None)
            continue
        current[key] = normalize_deck_color(key, value)
    return current or None


def company_deck_record(
    *,
    organization_id: uuid.UUID,
    close_month: str | None,
    fiscal_year_end_month: int,
    palette_raw: object,
    template_filename: str | None,
) -> dict[str, object]:
    """The company facts the board deck reads. Our deck until they store a presentation."""
    stored = stored_palette(palette_raw)
    colors = effective_palette(palette_raw)
    return {
        "organization_id": str(organization_id),
        "close_month": close_month,
        "fiscal_year_end_month": int(fiscal_year_end_month or 12),
        "presentation": "company" if template_filename else "ours",
        "template_filename": template_filename,
        "palette_custom": bool(stored),
        "palette_stored": {key: _display(value) for key, value in stored.items()},
        "palette": {key: _display(value) for key, value in colors.items()},
    }
