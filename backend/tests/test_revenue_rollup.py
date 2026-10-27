"""Revenue roll-up: the model may say only the relationships the engine marked."""

from __future__ import annotations

from app.services.commentary.revenue_rollup import (
    RevenueSectionIn,
    analyze_revenue_rollup,
    build_revenue_evidence,
    check_revenue_paragraph,
)


class FakeClient:
    def __init__(self, paragraph: str) -> None:
        self.paragraph = paragraph

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        return {"paragraph": self.paragraph}


def _section(lines, variance, comparison="Jun 2026 vs May 2026"):
    return RevenueSectionIn.model_validate(
        {
            "comparison": comparison,
            "materiality": 10000,
            "parent": {
                "label": "Revenue",
                "current": 7400000,
                "comparison_amount": 7400000 - variance,
                "variance": variance,
            },
            "lines": lines,
        }
    )


SUPPORTED = _section(
    [
        {
            "label": "Subscription Revenue",
            "variance": 300000,
            "facts": [
                {"label": "customers", "current": 756, "base": 745},
                {"label": "average subscription revenue", "current": 8791, "base": 8491},
            ],
        },
        {
            "label": "Recurring Services",
            "variance": 20000,
            "facts": [
                {"label": "customers on recurring services", "current": 769, "base": 762},
                {"label": "average recurring services fee", "current": 872, "base": 868},
            ],
        },
    ],
    320000,
)

OFFSET = _section(
    [
        {
            "label": "Subscription Revenue",
            "variance": 500000,
            "facts": [{"label": "customers", "current": 756, "base": 745}],
        },
        {
            "label": "Recurring Services",
            "variance": -480000,
            "facts": [{"label": "average recurring services fee", "current": 800, "base": 872}],
        },
        {
            "label": "Implementation & Onboarding",
            "variance": 2000,
            "facts": [{"label": "expected customers", "current": 8, "base": 8}],
        },
    ],
    22000,
)

PARTIAL = _section(
    [
        {
            "label": "Subscription Revenue",
            "variance": 300000,
            "facts": [{"label": "customers", "current": 756, "base": 745}],
        },
        {"label": "Implementation & Onboarding", "variance": 80000},
    ],
    380000,
)


def test_supported_movement_has_no_offset_and_no_gap():
    evidence = build_revenue_evidence(SUPPORTED)
    kinds = [item["kind"] for item in evidence["relationships"]]
    assert kinds == ["with_total", "with_total"]
    assert evidence["largely"] is False


def test_offsetting_lines_are_marked_largely_when_the_net_is_small():
    evidence = build_revenue_evidence(OFFSET)
    offset = [item for item in evidence["relationships"] if item["kind"] == "offset"]
    assert offset[0]["label"] == "Recurring Services"
    assert offset[0]["largely"] is True
    assert evidence["largely"] is True


def test_partial_line_keeps_an_unexplained_amount():
    evidence = build_revenue_evidence(PARTIAL)
    gaps = [item for item in evidence["relationships"] if item["kind"] == "unexplained"]
    assert len(gaps) == 1
    assert gaps[0]["label"] == "Implementation & Onboarding"
    assert gaps[0]["amount"] == 80000
    assert gaps[0]["must_name"] is True


def test_supported_paragraph_passes_and_an_invented_cause_falls_back():
    evidence = build_revenue_evidence(SUPPORTED)
    ok, reason = check_revenue_paragraph(
        "Revenue rose 320,000 vs May 2026. Subscription Revenue rose 300,000, "
        "with customers from 745 to 756 and average subscription revenue from 8,491 to 8,791. "
        "Recurring Services rose 20,000.",
        evidence,
    )
    assert ok, reason
    bad, why = check_revenue_paragraph(
        "Revenue rose 320,000 because Engineering hired 4.",
        evidence,
    )
    assert bad is False
    assert why

    passed = analyze_revenue_rollup(
        SUPPORTED,
        FakeClient(
            "Revenue rose 320,000 vs May 2026. Subscription Revenue rose 300,000. Recurring Services rose 20,000."
        ),
    )
    assert passed.status == "ai"
    invented = analyze_revenue_rollup(
        SUPPORTED,
        FakeClient("Revenue rose 320,000 because Engineering hired 4."),
    )
    assert invented.status == "fallback"
    assert invented.paragraph == ""
    assert invented.evidence["relationships"]


def test_largely_is_rejected_when_the_offset_does_not_dominate():
    evidence = build_revenue_evidence(SUPPORTED)
    ok, reason = check_revenue_paragraph(
        "Revenue rose 320,000 and was largely offset by lower Recurring Services of 20,000, leaving revenue nearly flat.",
        evidence,
    )
    assert ok is False
    assert "largely" in reason


def test_offset_paragraph_can_say_largely_and_partial_must_name_the_gap():
    offset_evidence = build_revenue_evidence(OFFSET)
    ok, reason = check_revenue_paragraph(
        "Revenue rose 22,000 vs May 2026. Subscription Revenue rose 500,000 and was largely offset by lower Recurring Services of 480,000, leaving revenue nearly flat.",
        offset_evidence,
    )
    assert ok, reason

    partial_evidence = build_revenue_evidence(PARTIAL)
    named, named_reason = check_revenue_paragraph(
        "Revenue rose 380,000 vs May 2026. Subscription Revenue rose 300,000, with customers from 745 to 756. "
        "Implementation & Onboarding moved 80,000, and 80,000 is unexplained.",
        partial_evidence,
    )
    assert named, named_reason
    skipped, skip_reason = check_revenue_paragraph(
        "Revenue rose 380,000 vs May 2026 because customers rose from 745 to 756.",
        partial_evidence,
    )
    assert skipped is False
    assert "unexplained" in skip_reason


def test_missing_model_returns_the_evidence_and_a_fallback():
    result = analyze_revenue_rollup(OFFSET, None)
    assert result.status == "fallback"
    assert result.evidence["largely"] is True
    assert any(item["kind"] == "offset" for item in result.evidence["relationships"])


JUNE = _section(
    [
        {
            "label": "4000 Subscription Revenue",
            "variance": 94649,
            "facts": [
                {"label": "customers", "current": 769, "base": 762},
                {"label": "average subscription revenue", "current": 8721.02, "base": 8676.93},
            ],
        },
        {"label": "4200 Recurring Services", "variance": 9465},
        {"label": "4100 Implementation & Onboarding", "variance": -8000},
    ],
    96114,
)


def test_smaller_lines_stay_in_the_story_and_the_headline_can_be_omitted():
    evidence = build_revenue_evidence(JUNE)
    labels = [item["label"] for item in evidence["relationships"]]
    assert "4200 Recurring Services" in labels
    assert "4100 Implementation & Onboarding" in labels
    offset = [item for item in evidence["relationships"] if item["kind"] == "offset"]
    assert offset[0]["variance"] == -8000
    assert offset[0]["largely"] is False
    ok, reason = check_revenue_paragraph(
        "Subscription revenue rose 94,649 as customers went from 762 to 769 and average subscription revenue went from 8,676.93 to 8,721.02. "
        "Recurring services rose 9,465, partly offset by lower implementation of 8,000.",
        evidence,
    )
    assert ok, reason
    scaled, scaled_reason = check_revenue_paragraph(
        "Revenue reached 7.4 million. Subscription revenue rose 94,649, recurring services rose 9,465, and implementation was lower by 8,000.",
        evidence,
    )
    assert scaled, scaled_reason
