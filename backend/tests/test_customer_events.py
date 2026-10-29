"""Large customers are named on the month and on the forecast. Budget stays a number."""

from __future__ import annotations

import uuid

from app.services.commentary.customer_events import brief_lost, brief_movements, pipeline_review
from app.services.commentary.revenue_rollup import (
    ROLLUP_SYSTEM,
    RevenueSectionIn,
    analyze_revenue_rollup,
    attach_stored_events,
    build_revenue_evidence,
    check_revenue_paragraph,
    separate_lines,
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


def test_a_customer_id_can_be_written_or_left_off():
    section = _section(
        events=[
            {
                "bucket": "Expansion",
                "customer": "Summit Analytics 166",
                "amount": 165049.23,
                "others": 6,
                "others_amount": 704087.4,
                "outcome": "occurred",
            }
        ]
    )
    evidence = build_revenue_evidence(section)
    with_id = (
        "Subscription Revenue rose $350.00k. "
        "Expansion included Summit Analytics 166 at $165.05k, and 6 others at $704.09k."
    )
    ok, reason = check_revenue_paragraph(with_id, evidence)
    assert ok, reason
    without_id = (
        "Subscription Revenue rose $350.00k. "
        "Expansion included Summit Analytics at $165.05k, and 6 others at $704.09k."
    )
    ok, reason = check_revenue_paragraph(without_id, evidence)
    assert ok, reason


def test_a_missing_customer_is_added_from_the_event():
    class Client:
        def generate(self, *, system_prompt, user_prompt):
            return {"paragraph": "Subscription Revenue rose $350.00k. The increase included Enterprise."}

    section = _section(
        events=[
            {
                "bucket": "Expansion",
                "customer": "Summit Analytics 166",
                "amount": 165049.23,
                "others": 0,
                "others_amount": 0,
                "outcome": "occurred",
            }
        ]
    )
    result = analyze_revenue_rollup(section, Client())
    assert result.status == "ai", result.reason
    assert "Summit Analytics" in result.paragraph
    assert "Enterprise" not in result.paragraph


def test_an_extra_name_does_not_block_the_month():
    class Client:
        def generate(self, *, system_prompt, user_prompt):
            return {"paragraph": "Subscription Revenue rose $350.00k. The increase included Enterprise."}

    result = analyze_revenue_rollup(_section(), Client())
    assert result.status == "ai", result.reason
    assert "Enterprise" not in result.paragraph
    assert "$350.00k" in result.paragraph


def test_each_group_starts_on_its_own_line():
    text = (
        "General and administrative increased $7.51k in June 2026 versus May 2026. "
        "G&A increased $17.15k. Finance decreased $9.72k. Support increased $83.45."
    )
    broken = separate_lines(text, {"lines": [{"label": "G&A"}, {"label": "Finance"}, {"label": "Support"}]})
    assert "\nG&A increased" in broken
    assert "\nFinance decreased" in broken
    assert "\nSupport increased" in broken


def test_a_department_named_inside_a_sentence_stays_there():
    text = (
        "Sales and marketing increased $10.98k to $2.66m in June 2026 versus May 2026. "
        "Marketing drove the increase with $15.73k higher spending, primarily from\n"
        "Marketing Programs at $15.75k, partially offset by $22.45 lower Travel & Entertainment. "
        "Customer Success decreased $2.75k, with a partial offset from $426.66 higher\n"
        "Sales Travel against $3.18k lower\n"
        "Sales Commissions—Expensed. "
        "Sales declined $2.00k, with a partial offset from $5.93k higher\n"
        "Sales Travel and $843.38 higher\n"
        "Sales Tools against $5.92k lower Base Salaries."
    )
    broken = separate_lines(
        text,
        {"lines": [{"label": "Marketing"}, {"label": "Customer Success"}, {"label": "Sales"}]},
    )
    assert "\nMarketing drove" in broken
    assert "\nCustomer Success decreased" in broken
    assert "\nSales declined" in broken
    assert "from Marketing Programs" in broken
    assert "higher Sales Travel" in broken
    assert "lower Sales Commissions" in broken
    assert "higher Sales Tools" in broken
    assert "\nMarketing Programs" not in broken
    assert "\nSales Travel" not in broken
    assert "\nSales Tools" not in broken
    assert "\nSales Commissions" not in broken


def test_several_lines_are_written_as_separate_sentences():
    assert "line break" in ROLLUP_SYSTEM
    assert "colon" in ROLLUP_SYSTEM


def test_the_event_bucket_is_not_an_unknown_customer():
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
        "Subscription Revenue rose $350.00k. The month included New Business, Apex Works at $40.00k.",
        evidence,
    )
    assert ok, reason


def test_naming_a_revenue_line_is_not_a_customer():
    evidence = build_revenue_evidence(_section())
    ok, reason = check_revenue_paragraph(
        "The increase included Subscription Revenue, which rose $350.00k.",
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


def test_closed_lost_customers_stay_with_their_opportunity_type():
    briefs = brief_lost(
        [
            {"customer": "Northstar Works 630", "type": "New Business", "amount": 80000, "outcome": "lost"},
            {"customer": "Apex Group 36", "type": "New Business", "amount": 25000, "outcome": "lost"},
            {"customer": "Summit Analytics 166", "type": "Expansion", "amount": 40000, "outcome": "lost"},
            {"customer": "Too Small", "type": "New Business", "amount": 500, "outcome": "lost"},
            {"customer": "Won Deal", "type": "New Business", "amount": 90000, "outcome": "won"},
        ],
        10000,
    )
    assert [item["bucket"] for item in briefs] == ["New Business", "Expansion"]
    assert briefs[0]["customer"] == "Northstar Works 630"
    assert briefs[0]["others"] == 1
    assert briefs[0]["others_amount"] == 25000
    assert briefs[1]["customer"] == "Summit Analytics 166"
    assert briefs[1]["others"] == 0


def test_the_discussion_loads_the_same_customer_briefs(monkeypatch):
    monkeypatch.setattr("app.api.commentary_routes.get_organization_or_404", lambda db, org, module="board_export": object())
    monkeypatch.setattr(
        "app.services.reporting.source_trace.customer_movements",
        lambda db, org, period: [{"customer": "Evergreen Solutions 603", "type": "Expansion", "amount": 197020}],
    )
    from app.api.commentary_routes import customer_events_for

    loaded = customer_events_for(ORG, "2026-06", "mom", object())
    assert loaded["events"][0]["customer"] == "Evergreen Solutions 603"
    assert loaded["events"][0]["bucket"] == "Expansion"
    assert customer_events_for(ORG, "2026-06", "budget", object()) == {"events": [], "lost": []}


def test_the_month_loads_customers_from_the_books(monkeypatch):
    monkeypatch.setattr(
        "app.services.reporting.source_trace.customer_movements",
        lambda db, org, period: [{"customer": "Apex Works", "type": "Expansion", "amount": 22000}],
    )
    attached = attach_stored_events(_section(), object())
    assert [event.customer for event in attached.events] == ["Apex Works"]
    assert attached.events[0].bucket == "Expansion"
    assert uuid.UUID(ORG)
