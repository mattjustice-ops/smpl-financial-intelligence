"""Situations a revenue paragraph can meet.

Each row is evidence the engine can emit, including shapes this company's books
do not show. The allowed sentence must pass. Each rejected sentence must fail.
Nothing here calls the model.
"""

from __future__ import annotations

import pytest

from app.services.commentary.revenue_rollup import (
    RevenueSectionIn,
    build_revenue_evidence,
    check_revenue_paragraph,
)


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


CATALOG = [
    {
        "name": "a month states its own facts and does not invent a comparison",
        "section": _section(
            [
                {
                    "label": "4000 Subscription Revenue",
                    "variance": 300000,
                    "facts": [
                        {"label": "customers", "current": 756, "base": 745},
                        {"label": "average subscription revenue", "current": 8791, "base": 8491},
                    ],
                },
                {
                    "label": "4200 Recurring Services",
                    "variance": 20000,
                    "facts": [{"label": "customers ended", "current": 4, "base": 2}],
                },
            ],
            320000,
        ),
        "allow": (
            "4000 Subscription Revenue rose $300.00k as customers rose from 745 to 756 and the average rose $0.30k. "
            "4 customers churned, versus 2. Recurring services rose $20.00k."
        ),
        "rejects": [
            ("Recurring services offset the increase.", "offset"),
            ("Subscription outpaced recurring services and rose $300.00k.", "pattern"),
            ("Revenue rose $320.00k for the third straight month.", "pattern"),
            ("Revenue rose $320.00k for the fiscal year.", "pattern"),
            ("Revenue rose $320.00k on a higher run rate.", "pattern"),
            ("That leaves $320.00k available to spend.", "pattern"),
            ("Subscription rose $300.00k, driven by stronger pricing.", "pricing"),
            ("We implemented 3 Enterprise customers, versus 1.", "3"),
        ],
    },
    {
        "name": "a quarter with no schedule states dollars only",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 831930},
                {"label": "4100 Implementation & Onboarding", "variance": -11500},
            ],
            820430,
            comparison="Q2 2026 vs Q1 2026",
        ),
        "allow": "In Q2, 4000 Subscription Revenue rose $831.93k. Onboarding was lower by $11.50k.",
        "rejects": [
            ("Customers rose from 10 to 12.", "10"),
            ("The reason for the $831.93k variance is unexplained.", "unexplained"),
            ("Onboarding largely offset the increase.", "largely"),
        ],
    },
    {
        "name": "a year to date with no schedule does not borrow one month's customers",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 831930},
                {"label": "4100 Implementation & Onboarding", "variance": -11500},
            ],
            820430,
            comparison="YTD Jun 2026 vs YTD Jun 2025",
        ),
        "allow": "4000 Subscription Revenue rose $831.93k. Onboarding was lower by $11.50k.",
        "rejects": [
            ("Customers rose from 637 to 756.", "637"),
            ("Revenue fell for three consecutive months.", "pattern"),
        ],
    },
    {
        "name": "a year over year change may cite a fact's own difference",
        "section": _section(
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
        ),
        "allow": (
            "Subscription revenue rose $1.87m as customers rose by 119 and the average rose $0.04k. "
            "Onboarding declined $11.50k as implementations declined from 13 to 8."
        ),
        "rejects": [
            ("Subscription revenue rose $1.87m, driven by stronger pricing.", "pricing"),
        ],
    },
    {
        "name": "budget names the comparison",
        "section": _section(
            [{"label": "4000 Subscription Revenue", "variance": 150000}],
            150000,
            comparison="Jun 2026 vs Budget",
        ),
        "allow": "4000 Subscription Revenue rose $150.00k versus Budget.",
        "rejects": [
            ("Subscription revenue rose $150.00k, driven by the budget.", "budget"),
        ],
    },
    {
        "name": "forecast names the comparison",
        "section": _section(
            [{"label": "4000 Subscription Revenue", "variance": 150000}],
            150000,
            comparison="Jun 2026 vs Forecast",
        ),
        "allow": "4000 Subscription Revenue rose $150.00k versus Forecast.",
        "rejects": [
            ("Subscription revenue rose $150.00k, driven by the forecast.", "forecast"),
        ],
    },
    {
        "name": "a decline can name the line that went the other way",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": -250000},
                {"label": "4100 Implementation & Onboarding", "variance": 50000},
            ],
            -200000,
        ),
        "allow": "Subscription revenue fell $250.00k. Onboarding was higher by $50.00k.",
        "rejects": [
            ("Onboarding largely offset the decline.", "largely"),
        ],
    },
    {
        "name": "an offset below materiality is not a large offset",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 11500},
                {"label": "4100 Implementation & Onboarding", "variance": -9500},
            ],
            2000,
        ),
        "allow": "Subscription rose $11.50k. Onboarding was lower by $9.50k.",
        "rejects": [
            ("Onboarding largely offset subscription.", "largely"),
        ],
    },
    {
        "name": "a large offset may be called large",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 500000},
                {"label": "4200 Recurring Services", "variance": -480000},
            ],
            22000,
        ),
        "allow": "Subscription rose $500.00k and was largely offset by lower recurring services of $480.00k.",
        "rejects": [
            ("Subscription rose $500.00k, driven by a price increase.", "price"),
        ],
    },
    {
        "name": "a gap between the lines and the total has to be named",
        "section": _section(
            [
                {"label": "4000 Subscription Revenue", "variance": 300000},
                {"label": "4100 Implementation & Onboarding", "variance": 80000},
            ],
            410000,
        ),
        "allow": "Subscription rose $300.00k. Onboarding rose $80.00k. Other revenue of $30.00k is unexplained.",
        "rejects": [
            ("Subscription rose $300.00k. Onboarding rose $80.00k.", "30,000"),
            ("The other $30.00k was driven by a new product.", "product"),
        ],
    },
    {
        "name": "one decimal is the same loaded amount",
        "section": _section(
            [{"label": "4100 Implementation & Onboarding", "variance": 71590}],
            71590,
            comparison="Q2 2026 vs Q1 2026",
        ),
        "allow": "Onboarding rose $71.5k.",
        "also": ["Onboarding rose 71.5k.", "Onboarding rose $71.59k."],
        "rejects": [
            ("Onboarding rose $71.50k.", "71.50k"),
            ("Onboarding rose $715.90k.", "715.90k"),
        ],
    },
    {
        "name": "a fee under one thousand keeps its dollars",
        "section": _section(
            [{"label": "4200 Recurring Services", "variance": 868}],
            868,
        ),
        "allow": "Recurring services rose $868.00.",
        "also": ["Recurring services rose $0.87k."],
        "rejects": [
            ("Recurring services rose $1.00k.", "1.00k"),
        ],
    },
    {
        "name": "zero implementations can be named when the count is loaded",
        "section": _section(
            [
                {
                    "label": "4100 Implementation & Onboarding",
                    "variance": -39000,
                    "facts": [{"label": "implementations", "current": 0, "base": 12}],
                }
            ],
            -39000,
        ),
        "allow": "Onboarding fell $39.00k as implementations fell from 12 to 0.",
        "rejects": [
            ("Onboarding fell $39.00k, driven by pipeline.", "pipeline"),
        ],
    },
]


@pytest.mark.parametrize("case", CATALOG, ids=[case["name"] for case in CATALOG])
def test_revenue_situation(case):
    evidence = build_revenue_evidence(case["section"])
    allowed, reason = check_revenue_paragraph(case["allow"], evidence)
    assert allowed, f"{case['name']}: {reason}"
    for sentence in case.get("also") or []:
        extra, extra_reason = check_revenue_paragraph(sentence, evidence)
        assert extra, f"{case['name']}: {extra_reason}"
    for sentence, snippet in case["rejects"]:
        rejected, why = check_revenue_paragraph(sentence, evidence)
        assert rejected is False, case["name"]
        assert snippet in why, f"{case['name']}: {why}"
