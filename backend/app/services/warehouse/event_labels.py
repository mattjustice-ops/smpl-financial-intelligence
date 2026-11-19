"""How a customer's own words land on a waterfall line.

The defaults cover the words in our example files. A company replaces or extends
them with ``organizations.contract_event_labels`` once that column exists:

    {"movements": {"logo": "new", "downgrade": "contraction"},
     "closed_won": ["booked"]}

``movements`` adds to the defaults. ``closed_won``, when present, is the whole
list of words that count as a booking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MOVEMENT_LINES = ("new", "expansion", "contraction", "churn", "reactivation")

DEFAULT_MOVEMENTS: dict[str, str] = {
    "new": "new",
    "new business": "new",
    "new logo": "new",
    "new_logo": "new",
    "logo": "new",
    "expansion": "expansion",
    "upsell": "expansion",
    "first year expansion": "expansion",
    "first_year_expansion": "expansion",
    "contraction": "contraction",
    "downgrade": "contraction",
    "first year contraction": "contraction",
    "first_year_contraction": "contraction",
    "churn": "churn",
    "cancel": "churn",
    "cancellation": "churn",
    "pause": "churn",
    "no start": "churn",
    "no_start": "churn",
    "reactivation": "reactivation",
    "winback": "reactivation",
    "restart": "reactivation",
}

DEFAULT_CLOSED_WON = frozenset({"closed won", "won", "closed"})


def _words(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


@dataclass
class EventLabels:
    movements: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MOVEMENTS))
    closed_won: frozenset[str] = DEFAULT_CLOSED_WON

    def movement(self, *raw_values: Any) -> str | None:
        for raw in raw_values:
            word = _words(raw)
            if word and word in self.movements:
                line = self.movements[word]
                if line in MOVEMENT_LINES:
                    return line
        return None

    def is_closed_won(self, *raw_values: Any) -> bool:
        return any(_words(raw) in self.closed_won for raw in raw_values if _words(raw))


def labels_from_json(raw: Any) -> EventLabels:
    labels = EventLabels()
    if not isinstance(raw, dict):
        return labels
    extra = raw.get("movements")
    if isinstance(extra, dict):
        for key, line in extra.items():
            word = _words(key)
            target = _words(line).replace(" ", "_")
            target = {"new_business": "new", "new_logo": "new"}.get(target, target)
            if word and target in MOVEMENT_LINES:
                labels.movements[word] = target
    closed = raw.get("closed_won")
    if isinstance(closed, list) and closed:
        labels.closed_won = frozenset(_words(item) for item in closed if _words(item))
    return labels
