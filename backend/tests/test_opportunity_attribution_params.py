"""Opportunity attribution accepts dashboard params from executive_flow."""

from __future__ import annotations

import inspect

from app.services.dashboard.opportunity_attribution_service import opportunity_attribution


def test_opportunity_attribution_accepts_as_of_period_kwarg() -> None:
    params = inspect.signature(opportunity_attribution).parameters
    assert "as_of_period" in params
    assert params["as_of_period"].default is None
