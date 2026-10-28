"""Large customers are named on the month and on the forecast. Budget stays a number."""

from __future__ import annotations

import uuid

from app.services.commentary.customer_events import brief_movements, pipeline_review
from app.services.commentary.revenue_rollup import (
    RevenueSectionIn,
    attach_stored_events,
    build_revenue_evidence,
    check_revenue_paragraph,
)

ORG = "8571e520-0687-4516-bdee-379f37c58c1f"


def _section(**extra):
    body = {
        "comparison": "Jun 2026 vs May 2026",
        "comparison_kind": "mom",
        "section_id": "revenue",
        "period": "2026-06",
        "organization_id": ORG,
        "materiality": 10000,
        "parent": {"label": "Revenue", "current": 7350000, "comparison_amount": 7000000, "variance": 350000},
        "lines": [
            {
                "label": "Subscription Revenue",
                "current": 7350000,
                "comparison_amount": 7000000,
                "variance": 350000,
            }
        ],
    }
    body.update(extra)
    return RevenueSectionIn.model_validate(body)


def test_a_small_customer_is_left_out():
    events = brief_movements(
        [
            {"customer": "Apex Works", "type": "New Business", "amount": 40000},
            {"customer": "Small Co", "type": "New Business", "amount": 500},
            {"customer": "Northwind", "type": "Churn", "amount": -80000},
        ],
        10000,
    )
    assert [(event["bucket"], event["customer"], event["amount"]) for event in events] == [
        ("New Business", "Apex Works", 40000),
        ("Churn", "Northwind", 80000),
    ]
    assert events[0]["outcome"] == "occurred"
    assert events[0]["others"] == 0


def test_other_large_customers_are_a_count():
    events = brief_movements(
        [
            {"customer": "Apex Works", "type": "New Business", "amount": 40000},
            {"customer": "BlueRiver Legal", "type": "New Business", "amount": 25000},
            {"customer": "Harbor", "type": "New Business", "amount": 15000},
        ],
        10000,
    )
    assert events[0]["customer"] == "Apex Works"
    assert events[0]["others"] == 2
    assert events[0]["others_amount"] == 40000


def test_forecast_splits_what_came_in_from_what_did_not():
    expected = [
        {"id": "1", "customer": "Apex Works", "arr": 40000, "outcome": "open"},
        {"id": "2", "customer": "Northwind", "arr": 50000, "outcome": "open"},
        {"id": "3", "customer": "Small Co", "arr": 1000, "outcome": "open"},
    ]
    closed = [{"id": "1", "customer": "Apex Works", "arr": 40000, "outcome": "won"}]
    events = pipeline_review(expected, closed, 10000)
    by_outcome = {event["outcome"]: event["customer"] for event in events}
    assert by_outcome == {"came in": "Apex Works", "did not come in": "Northwind"}


def test_the_paragraph_may_name_the_loaded_customer():
    section = _section(
        events=[
            {
                "bucket": "New Business",
                "customer": "Apex Works",
                "amount": 40000,
                "others": 0,
                "others_amount": 0,
                "outcome": "occurred",
            }
        ]
    )
    evidence = build_revenue_evidence(section)
    ok, reason = check_revenue_paragraph(
        "Subscription Revenue rose $350.00k. New Business included Apex Works at $40.00k.",
        evidence,
    )
    assert ok, reason


def test_an_unnamed_customer_is_rejected():
    section = _section(
        events=[
            {
                "bucket": "New Business",
                "customer": "Apex Works",
                "amount": 40000,
                "outcome": "occurred",
            }
        ]
    )
    evidence = build_revenue_evidence(section)
    ok, reason = check_revenue_paragraph(
        "Subscription Revenue rose $350.00k. New Business included Northwind at $40.00k.",
        evidence,
    )
    assert not ok
    assert "customer" in reason


def test_a_missing_large_customer_is_rejected():
    section = _section(
        events=[
            {
                "bucket": "New Business",
                "customer": "Apex Works",
                "amount": 40000,
                "outcome": "occurred",
            }
        ]
    )
    evidence = build_revenue_evidence(section)
    ok, reason = check_revenue_paragraph("Subscription Revenue rose $350.00k.", evidence)
    assert not ok
    assert "Apex Works" in reason


def test_budget_and_other_sections_do_not_keep_customers():
    seeded = _section(
        comparison_kind="budget",
        events=[{"bucket": "New Business", "customer": "Apex Works", "amount": 40000, "outcome": "occurred"}],
    )
    assert attach_stored_events(seeded, object()).events == []
    quarter = _section(comparison_kind="qoq")
    assert attach_stored_events(quarter, object()).events == []
    cost = _section(section_id="cogs")
    assert attach_stored_events(cost, object()).events == []


def test_the_month_loads_customers_from_the_books(monkeypatch):
    monkeypatch.setattr(
        "app.services.reporting.source_trace.customer_movements",
        lambda db, org, period: [{"customer": "Apex Works", "type": "Expansion", "amount": 22000}],
    )
    attached = attach_stored_events(_section(), object())
    assert [event.customer for event in attached.events] == ["Apex Works"]
    assert attached.events[0].bucket == "Expansion"
    assert uuid.UUID(ORG)
