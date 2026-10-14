from __future__ import annotations

import uuid

import pytest


@pytest.fixture(autouse=True)
def warehouse_without_closed_history(monkeypatch):
    """The SQLite test databases hold no warehouse tables: an organization's prior history reads as empty."""

    from app.api import predictive_planning_routes as routes

    monkeypatch.setattr(routes, "resolve_org_close_month", lambda db, org: "2026-06")
    monkeypatch.setattr(
        routes,
        "build_prior_history",
        lambda db, organization_id, *, as_of: {"monthly_ending_arr": [], "periods": [], "source": "warehouse"},
    )


@pytest.fixture()
def plan_assurance_member(monkeypatch):
    """Treat every Plan Assurance request as coming from a member of its organization.

    For tests of assessment behavior. Authorization itself is covered in
    test_plan_assurance_auth.py, which does not use this fixture.
    """

    from app.api import predictive_planning_routes as routes

    user_id = uuid.uuid4()
    monkeypatch.setattr(routes, "_require_user", lambda: user_id)
    monkeypatch.setattr(routes, "_require_org_member", lambda db, organization_id: user_id)
    return user_id
