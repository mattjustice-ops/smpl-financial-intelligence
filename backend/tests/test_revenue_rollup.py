"""Revenue roll-up: the model may say only the relationships the engine marked."""

from __future__ import annotations

from app.services.commentary.revenue_rollup import (
    ROLLUP_SYSTEM,
    RevenueSectionIn,
    analyze_revenue_rollup,
    build_revenue_evidence,
    check_revenue_paragraph,
    present_revenue_evidence,
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


def test_a_line_without_a_driver_is_not_called_unexplained():
    evidence = build_revenue_evidence(PARTIAL)
    assert [item for item in evidence["relationships"] if item["kind"] == "unexplained"] == []
    ok, reason = check_revenue_paragraph(
        "Revenue rose $380.00k vs May 2026. Subscription Revenue rose $300.00k, with customers from 745 to 756. "
        "Implementation & Onboarding rose $80.00k.",
        evidence,
    )
    assert ok, reason
    called, why = check_revenue_paragraph(
        "Implementation & Onboarding rose $80.00k, and $80.00k is unexplained.",
        evidence,
    )
    assert called is False
    assert "unexplained" in why


def test_a_driver_remainder_stays_unexplained():
    evidence = build_revenue_evidence(
        _section(
            [
                {
                    "label": "Subscription Revenue",
                    "variance": 300000,
                    "facts": [{"label": "customers", "current": 756, "base": 745}],
                },
                {
                    "label": "Implementation & Onboarding",
                    "variance": 80000,
                    "drivers": [{"label": "One deal", "variance": 50000}],
                },
            ],
            380000,
        )
    )
    gaps = [item for item in evidence["relationships"] if item["kind"] == "unexplained"]
    assert len(gaps) == 1
    assert gaps[0]["amount"] == 30000
    assert gaps[0]["must_name"] is True


def test_account_number_is_allowed_and_the_total_is_not_the_reason():
    evidence = build_revenue_evidence(
        _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 831930},
                {"label": "4100 Implementation & Onboarding", "variance": -11500},
            ],
            820430,
            comparison="Q2 2026 vs Q1 2026",
        )
    )
    ok, reason = check_revenue_paragraph(
        "4000 Subscription Revenue rose $831.93k. Onboarding was lower by $11.50k.",
        evidence,
    )
    assert ok, reason
    restated, why = check_revenue_paragraph(
        "Subscription revenue moved with total revenue, increasing $831.93k. Onboarding was lower by $11.50k.",
        evidence,
    )
    assert restated is False
    assert "total" in why
    invented, invented_why = check_revenue_paragraph(
        "4000 Subscription Revenue rose $831.93k versus budget, driven by stronger pricing. Onboarding was lower by $11.50k.",
        evidence,
    )
    assert invented is False
    assert "pricing" in invented_why
    quarter, quarter_reason = check_revenue_paragraph(
        "In Q2, 4000 Subscription Revenue rose $831.93k. Onboarding was lower by $11.50k.",
        evidence,
    )
    assert quarter, quarter_reason
    leaked, leaked_why = check_revenue_paragraph(
        "4000 Subscription Revenue rose $831.93k with_total. Onboarding was lower by $11.50k.",
        evidence,
    )
    assert leaked is False
    assert "field" in leaked_why


def test_a_fact_change_ties_and_the_total_is_not_a_cause():
    evidence = build_revenue_evidence(
        _section(
            [
                {
                    "label": "4000 Subscription Revenue",
                    "variance": 1867263,
                    "facts": [
                        {"label": "customers", "current": 756, "base": 637},
                        {"label": "average subscription revenue", "current": 8721.02, "base": 8676.93},
                    ],
                },
                {"label": "4100 Implementation & Onboarding", "variance": -11500},
            ],
            1855763,
            comparison="Jun 2026 vs Jun 2025",
        )
    )
    ok, reason = check_revenue_paragraph(
        "Subscription revenue rose $1.87m as customers rose by 119 and average subscription revenue rose $0.04k. "
        "Onboarding declined $11.50k, offsetting the total increase.",
        evidence,
    )
    assert ok, reason
    with_implementations = build_revenue_evidence(
        _section(
            [
                {
                    "label": "4000 Subscription Revenue",
                    "variance": 1867263,
                    "facts": [
                        {"label": "customers", "current": 756, "base": 637},
                        {"label": "average subscription revenue", "current": 8721.02, "base": 8676.93},
                    ],
                },
                {
                    "label": "4100 Implementation & Onboarding",
                    "variance": -11500,
                    "facts": [{"label": "implementations", "current": 8, "base": 13}],
                },
            ],
            1855763,
            comparison="Jun 2026 vs Jun 2025",
        )
    )
    named_total, named_why = check_revenue_paragraph(
        "Subscription revenue rose $1.87m. Onboarding declined $11.50k, offsetting the total increase, "
        "as implementations declined from 13 to 8.",
        with_implementations,
    )
    assert named_total, named_why
    pricing, pricing_why = check_revenue_paragraph(
        "Onboarding declined $11.50k, offsetting the total increase as stronger pricing.",
        with_implementations,
    )
    assert pricing is False
    assert "pricing" in pricing_why
    invented, invented_why = check_revenue_paragraph(
        "Subscription revenue rose $1.87m, driven by stronger pricing. Onboarding declined $11.50k.",
        evidence,
    )
    assert invented is False
    assert "pricing" in invented_why


def test_supported_paragraph_passes_and_an_invented_cause_falls_back():
    evidence = build_revenue_evidence(SUPPORTED)
    ok, reason = check_revenue_paragraph(
        "Revenue rose $320.00k vs May 2026. Subscription Revenue rose $300.00k, "
        "with customers from 745 to 756 and average subscription revenue from $8.49k to $8.79k. "
        "Recurring Services rose $20.00k.",
        evidence,
    )
    assert ok, reason
    bad, why = check_revenue_paragraph(
        "Revenue rose $320.00k because Engineering hired 41.",
        evidence,
    )
    assert bad is False
    assert why

    passed = analyze_revenue_rollup(
        SUPPORTED,
        FakeClient(
            "Revenue rose $320.00k vs May 2026. Subscription Revenue rose $300.00k. Recurring Services rose $20.00k."
        ),
    )
    assert passed.status == "ai"
    invented = analyze_revenue_rollup(
        SUPPORTED,
        FakeClient("Revenue rose $320.00k because Engineering hired 41."),
    )
    assert invented.status == "fallback"
    assert invented.paragraph == ""
    assert invented.evidence["relationships"]


class SequenceClient:
    def __init__(self, paragraphs: list[str]) -> None:
        self.paragraphs = list(paragraphs)

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        return {"paragraph": self.paragraphs.pop(0)}


def test_a_rejected_paragraph_is_rewritten_once():
    rewritten = analyze_revenue_rollup(
        SUPPORTED,
        SequenceClient(
            [
                "Revenue rose $999.99k because Engineering hired 4.",
                "Revenue rose $320.00k vs May 2026. Subscription Revenue rose $300.00k. Recurring Services rose $20.00k.",
            ]
        ),
    )
    assert rewritten.status == "ai"
    assert rewritten.paragraph.startswith("Revenue rose $320.00k")


def test_a_partial_offset_keeps_the_paragraph_without_largely():
    quarter = _section(
        [
            {"label": "4000 Subscription Revenue", "variance": 831930},
            {"label": "4100 Implementation & Onboarding", "variance": -11500},
        ],
        820430,
        comparison="Q2 2026 vs Q1 2026",
    )
    evidence = build_revenue_evidence(quarter)
    assert evidence["largely"] is False
    overstated = analyze_revenue_rollup(
        quarter,
        FakeClient(
            "4000 Subscription Revenue rose $831.93k. Onboarding declined $11.50k, largely offsetting the increase, "
            "leaving revenue nearly flat."
        ),
    )
    assert overstated.status == "ai"
    assert "largely" not in overstated.paragraph.lower()
    assert "flat" not in overstated.paragraph.lower()
    assert "$11.50k" in overstated.paragraph
    still_wrong = analyze_revenue_rollup(
        quarter,
        FakeClient("Onboarding declined $99.00k, largely offsetting the increase."),
    )
    assert still_wrong.status == "fallback"


def test_largely_is_rejected_when_the_offset_does_not_dominate():
    evidence = build_revenue_evidence(SUPPORTED)
    ok, reason = check_revenue_paragraph(
        "Revenue rose $320.00k and was largely offset by lower Recurring Services of $20.00k, leaving revenue nearly flat.",
        evidence,
    )
    assert ok is False
    assert "largely" in reason


def test_offset_paragraph_can_say_largely_and_partial_must_name_the_gap():
    offset_evidence = build_revenue_evidence(OFFSET)
    ok, reason = check_revenue_paragraph(
        "Revenue rose $22.00k vs May 2026. Subscription Revenue rose $500.00k and was largely offset by lower Recurring Services of $480.00k, leaving revenue nearly flat.",
        offset_evidence,
    )
    assert ok, reason

    partial_evidence = build_revenue_evidence(PARTIAL)
    stated, stated_reason = check_revenue_paragraph(
        "Revenue rose $380.00k vs May 2026. Subscription Revenue rose $300.00k, with customers from 745 to 756. "
        "Implementation & Onboarding rose $80.00k.",
        partial_evidence,
    )
    assert stated, stated_reason


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
    full, full_reason = check_revenue_paragraph(
        "Subscription revenue rose 94,649 as customers went from 762 to 769 and average subscription revenue went from 8,676.93 to 8,721.02.",
        evidence,
    )
    assert full, full_reason
    wrong, wrong_reason = check_revenue_paragraph(
        "Subscription revenue rose $999.99k as customers went from 762 to 769.",
        evidence,
    )
    assert wrong is False
    assert wrong_reason
    ok, reason = check_revenue_paragraph(
        "Subscription revenue rose $94.65k as customers went from 762 to 769 and average subscription revenue went from $8.68k to $8.72k. "
        "Recurring services rose $9.47k, partly offset by lower implementation of $8.00k.",
        evidence,
    )
    assert ok, reason
    scaled, scaled_reason = check_revenue_paragraph(
        "Revenue reached $7.40m. Subscription revenue rose $94.65k, recurring services rose $9.47k, and implementation was lower by $8.00k.",
        evidence,
    )
    assert scaled, scaled_reason
    shown = present_revenue_evidence(evidence)
    subscription = shown["relationships"][0]
    assert subscription["variance"] == "$94.65k"
    customers = [fact for fact in subscription["facts"] if fact["label"] == "customers"][0]
    assert customers["current"] == 769 and customers["base"] == 762
    average = [fact for fact in subscription["facts"] if "average" in fact["label"]][0]
    assert average["current"] == "$8.72k" and average["base"] == "$8.68k"
    fees = present_revenue_evidence(
        build_revenue_evidence(
            _section(
                [
                    {
                        "label": "Implementation & Onboarding",
                        "variance": 550,
                        "facts": [{"label": "average implementation fee", "current": 4800, "base": 4250}],
                    }
                ],
                550,
            )
        )
    )
    fee = fees["relationships"][0]["facts"][0]
    assert fee["current"] == "$4.80k" and fee["base"] == "$4.25k"


def test_an_account_number_on_a_driver_is_part_of_the_name():
    evidence = build_revenue_evidence(
        _section(
            [
                {
                    "label": "Salaries and wages",
                    "variance": 12000,
                    "drivers": [{"label": "6100 Base Salaries", "variance": 12000}],
                }
            ],
            12000,
        )
    )
    ok, reason = check_revenue_paragraph(
        "Salaries and wages rose $12.00k, from 6100 Base Salaries.",
        evidence,
    )
    assert ok, reason
    missing, missing_reason = check_revenue_paragraph(
        "Salaries and wages rose $12.00k, from 6200 Base Salaries.",
        evidence,
    )
    assert missing is False
    assert "6200" in missing_reason


def test_one_decimal_is_the_same_loaded_amount():
    evidence = build_revenue_evidence(
        _section(
            [{"label": "Subscription Revenue", "variance": 16591.71}],
            16591.71,
        )
    )
    ok, reason = check_revenue_paragraph("Subscription Revenue rose $16.6k.", evidence)
    assert ok, reason
    exact, exact_reason = check_revenue_paragraph("Subscription Revenue rose $16.59k.", evidence)
    assert exact, exact_reason
    off, off_reason = check_revenue_paragraph("Subscription Revenue rose $16.50k.", evidence)
    assert off is False
    assert "$16.50k" in off_reason


def test_the_instructions_do_not_contain_a_sample_account_number():
    assert "4000" not in ROLLUP_SYSTEM
