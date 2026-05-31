"""Semantic layer helpers for board / MD&A exports (source-of-truth rules)."""

from __future__ import annotations

from app.services.reporting.export.reporting_period_engine import (
    PeriodMode,
    ReportingPeriodContext,
    build_period_context,
    periods_for_mode,
)
from app.services.reporting.export.saas_semantic_reporting import (
    MovementAttributionSummary,
    OpportunityMovementType,
    build_movement_attribution,
    build_revenue_lineage,
)
from app.services.reporting.export.executive_reporting_governance import (
    FORBIDDEN_DERIVATIONS,
    LIMITS,
    SOURCE_HIERARCHY,
    apply_density_governance,
    select_chart_kind,
    should_escalate_to_appendix,
)
from app.services.reporting.export.semantic_model import (
    SOURCE_OF_TRUTH,
    GlSemanticTags,
    OpportunitySemanticTags,
    classify_gl_row,
    classify_opportunity,
)

__all__ = [
    "FORBIDDEN_DERIVATIONS",
    "LIMITS",
    "SOURCE_HIERARCHY",
    "apply_density_governance",
    "select_chart_kind",
    "should_escalate_to_appendix",
    "SOURCE_OF_TRUTH",
    "GlSemanticTags",
    "OpportunitySemanticTags",
    "classify_gl_row",
    "classify_opportunity",
    "PeriodMode",
    "ReportingPeriodContext",
    "build_period_context",
    "periods_for_mode",
    "MovementAttributionSummary",
    "OpportunityMovementType",
    "build_movement_attribution",
    "build_revenue_lineage",
]
