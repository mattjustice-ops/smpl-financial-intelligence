"""Reusable executive components — fixed geometry, content slots only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ComponentId = Literal[
    "executive_kpi_strip",
    "period_scorecard_table",
    "commentary_panel",
    "executive_narrative_card",
    "section_divider",
    "source_metrics_table",
    "board_action_callout",
    "deal_spotlight_card",
    "appendix_dense_table",
    "chart_primary_frame",
    "footer_takeaway_band",
]


@dataclass(frozen=True)
class ComponentSpec:
    component_id: ComponentId
    zone: Literal["title", "kpi", "visual", "footer"]
    max_items: int
    reference: str


COMPONENT_REGISTRY: dict[ComponentId, ComponentSpec] = {
    "executive_kpi_strip": ComponentSpec(
        "executive_kpi_strip", "kpi", 4, "IMG_8039 KPI row"
    ),
    "period_scorecard_table": ComponentSpec(
        "period_scorecard_table", "visual", 6, "IMG_8039 TY/Plan/%/LY grid"
    ),
    "commentary_panel": ComponentSpec(
        "commentary_panel", "visual", 1, "CARET Slide13 orange column"
    ),
    "executive_narrative_card": ComponentSpec(
        "executive_narrative_card", "footer", 5, "MD&A What/Why/Impact cards"
    ),
    "section_divider": ComponentSpec(
        "section_divider", "visual", 1, "CARET Slide1 green section band"
    ),
    "source_metrics_table": ComponentSpec(
        "source_metrics_table", "visual", 5, "CARET channel / bookings tables"
    ),
    "board_action_callout": ComponentSpec(
        "board_action_callout", "visual", 6, "IMG_8050 strategy + risk matrix"
    ),
    "deal_spotlight_card": ComponentSpec(
        "deal_spotlight_card", "visual", 3, "Top opportunities spotlight"
    ),
    "appendix_dense_table": ComponentSpec(
        "appendix_dense_table", "visual", 12, "Validation / drilldown appendix"
    ),
    "chart_primary_frame": ComponentSpec(
        "chart_primary_frame", "visual", 1, "Single dominant chart — all story slides"
    ),
    "footer_takeaway_band": ComponentSpec(
        "footer_takeaway_band", "footer", 3, "Slide5 footer bullets max 3"
    ),
}

# Map template slots → components
SLOT_TO_COMPONENT: dict[str, ComponentId] = {
    "kpi_strip": "executive_kpi_strip",
    "period_table": "period_scorecard_table",
    "source_table": "source_metrics_table",
    "commentary_panel": "commentary_panel",
    "narrative_cards": "executive_narrative_card",
    "callout_matrix": "board_action_callout",
    "spotlight_cards": "deal_spotlight_card",
    "primary_chart": "chart_primary_frame",
    "section_narrative": "section_divider",
}
