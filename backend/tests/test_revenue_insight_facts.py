"""Insight-pack and ARR waterfall facts thicken revenue rollup evidence without inventing."""

from __future__ import annotations

import uuid

from app.services.commentary.revenue_rollup import (
    RevenueFactIn,
    RevenueSectionIn,
    attach_stored_events,
    build_revenue_evidence,
    check_revenue_paragraph,
    _insight_pack_facts,
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


def _subscription_fact_labels(section: RevenueSectionIn) -> list[str]:
    for line in section.lines:
        if "subscription" in line.label.lower():
            return [str(fact.label) for fact in line.facts]
    return []


def test_budget_keeps_events_empty_but_merges_arr_and_pack_facts(monkeypatch):
    monkeypatch.setattr(
        "app.services.commentary.revenue_rollup._arr_mom_facts",
        lambda db, org, period: [
            RevenueFactIn(label="expansion ARR", current=220000, base=180000)
        ],
    )
    monkeypatch.setattr(
        "app.services.commentary.revenue_rollup._insight_pack_facts",
        lambda db, org, period: [
            RevenueFactIn(label="net new ARR", amount=1_850_000),
            RevenueFactIn(label="recognized revenue", amount=7_350_000),
            RevenueFactIn(label="deferred ending", amount=1_200_000),
        ],
    )
    seeded = _section(
        comparison_kind="budget",
        comparison="Jun 2026 vs Budget",
        events=[{"bucket": "New Business", "customer": "Apex Works", "amount": 40000, "outcome": "occurred"}],
    )
    attached = attach_stored_events(seeded, object())
    assert attached.events == []
    labels = _subscription_fact_labels(attached)
    assert "expansion ARR" in labels
    assert "net new ARR" in labels
    assert "recognized revenue" in labels
    assert "deferred ending" in labels


def test_missing_packs_do_not_crash_or_invent(monkeypatch):
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.load_insight_packs",
        lambda db, org, period: None,
    )
    assert _insight_pack_facts(object(), uuid.UUID(ORG), "2026-06") == []
    monkeypatch.setattr(
        "app.services.commentary.revenue_rollup._arr_mom_facts",
        lambda db, org, period: [],
    )
    attached = attach_stored_events(_section(comparison_kind="budget"), object())
    assert attached.events == []
    assert _subscription_fact_labels(attached) == []


def test_mom_still_attaches_customers(monkeypatch):
    monkeypatch.setattr(
        "app.services.reporting.source_trace.customer_movements",
        lambda db, org, period: [{"customer": "Apex Works", "type": "Expansion", "amount": 22000}],
    )
    monkeypatch.setattr(
        "app.services.commentary.revenue_rollup._arr_mom_facts",
        lambda db, org, period: [],
    )
    monkeypatch.setattr(
        "app.services.commentary.revenue_rollup._insight_pack_facts",
        lambda db, org, period: [],
    )
    attached = attach_stored_events(_section(), object())
    assert [event.customer for event in attached.events] == ["Apex Works"]
    assert attached.events[0].bucket == "Expansion"


def test_paragraph_citing_pack_amounts_passes_when_in_evidence():
    section = _section(
        comparison_kind="budget",
        comparison="Jun 2026 vs Budget",
        lines=[
            {
                "label": "Subscription Revenue",
                "current": 7350000,
                "comparison_amount": 7000000,
                "variance": 350000,
                "facts": [
                    {"label": "net new ARR", "amount": 1_850_000},
                    {"label": "recognized revenue", "amount": 7_350_000},
                    {"label": "deferred ending", "amount": 1_200_000},
                    {"label": "gross retention rate", "amount": 0.985},
                    {"label": "churn ARR", "amount": 92000},
                    {"label": "trailing churn average", "amount": 70000},
                ],
            }
        ],
        events=[],
    )
    evidence = build_revenue_evidence(section)
    assert 1_850_000 in evidence["allowed_numbers"] or 1850000.0 in {
        float(item) for item in evidence["allowed_numbers"]
    }
    plain = {float(item) for item in evidence["plain_numbers"]}
    assert 98.5 in plain or any(abs(item - 98.5) < 0.05 for item in plain)
    ok, reason = check_revenue_paragraph(
        (
            "Subscription Revenue increased $350.00k to $7.35m; "
            "net new ARR $1.85m while recognized revenue was $7.35m; "
            "deferred ending $1.20m; gross retention rate 98.5; "
            "churn ARR $92.00k against trailing churn average $70.00k."
        ),
        evidence,
    )
    assert ok, reason


def test_insight_pack_facts_emit_only_non_null_fields(monkeypatch):
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.load_insight_packs",
        lambda db, org, period: {
            "arr_vs_revenue_deferred": {
                "net_new_arr": 1_200_000,
                "recognized_revenue": 6_500_000,
                "deferred_ending": 900_000,
                "deferred_beginning": None,
                "arr_vs_recognized_gap": None,
                "asc606_elements": {},
            },
            "customer_behavior": {
                "vs_run_rate": {
                    "churn_arr": 80_000,
                    "trailing_churn_avg": 50_000,
                    "churn_above_run_rate": 30_000,
                },
                "upgrade_subtype_mix": {},
                "uom_intensity": {},
            },
            "retention": {
                "gross_retention_rate": 0.97,
                "net_dollar_retention_rate": 1.05,
                "cohort_curves": {},
            },
        },
    )
    facts = _insight_pack_facts(object(), uuid.UUID(ORG), "2026-06")
    by_label = {fact.label: fact for fact in facts}
    assert by_label["net new ARR"].amount == 1_200_000
    assert by_label["recognized revenue"].amount == 6_500_000
    assert by_label["deferred ending"].amount == 900_000
    assert "deferred beginning" not in by_label
    assert by_label["churn ARR"].amount == 80_000
    assert by_label["gross retention rate"].amount == 0.97
    assert by_label["net dollar retention rate"].amount == 1.05
    assert all(isinstance(fact, RevenueFactIn) for fact in facts)
    assert not any("upgrade" in (fact.label or "").lower() for fact in facts)
