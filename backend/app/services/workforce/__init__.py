"""HRIS-style workforce operating intelligence."""

from app.services.workforce import feeds, service
from app.services.workforce.engine import WorkforcePlanningEngine

__all__ = ["WorkforcePlanningEngine", "feeds", "service"]
