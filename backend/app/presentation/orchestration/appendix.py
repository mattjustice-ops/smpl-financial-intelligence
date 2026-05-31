"""Appendix escalation — overflow tables/charts leave executive band."""

from __future__ import annotations

from app.services.reporting.export.board_appendix_engine import inject_appendix_slides
from app.services.reporting.export.executive_reporting_governance import should_escalate_to_appendix
from app.services.board_package.schemas import SlideContent

__all__ = ["inject_appendix_slides", "should_escalate_to_appendix"]
