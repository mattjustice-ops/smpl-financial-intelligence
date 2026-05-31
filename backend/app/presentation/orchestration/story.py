"""Storytelling orchestration — fixed narrative order and section cadence."""

from __future__ import annotations

from app.services.reporting.export.board_semantic_mappings import NARRATIVE_SLIDE_ORDER, SECTION_DIVIDERS
from app.services.reporting.export.board_story_chain import SECTION_TRANSITIONS

# Re-export canonical story chain (do not reorder at runtime)
STORY_ORDER = NARRATIVE_SLIDE_ORDER
SECTION_ANCHORS = SECTION_DIVIDERS
TRANSITION_META = SECTION_TRANSITIONS
