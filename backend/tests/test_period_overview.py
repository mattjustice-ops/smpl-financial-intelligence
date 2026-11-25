"""Period overview: cite packs and statement facts; salvage when the model invents."""

from __future__ import annotations

from app.services.commentary.period_overview import (
    PeriodOverviewIn,
    analyze_period_overview,
    attach_overview_packs,
    build_overview_evidence,
    check_overview_paragraph,
    deterministic_overview_paragraph,
)


class FakeClient:
    def __init__(self, paragraph: str) -> None:
        self.paragraph = paragraph
        self.calls = 0

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        self.calls += 1
        return {"paragraph": self.paragraph}


class SequenceClient:
    def __init__(self, paragraphs: list[str]) -> None:
        self.paragraphs = list(paragraphs)

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict:
        return {"paragraph": self.paragraphs.pop(0)}


def _section(**overrides):
    payload = {
        "comparison": "Jul 2026 vs Jun 2026",
        "comparison_kind": "mom",
        "period": "2026-07",
        "organization_id": "",
        "materiality": 10000,
        "lead": "In Jul 2026, ARR grew $400.00k to $42.00m, compared with Jun 2026's $350.00k gain.",
        "facts": [
            {
                "label": "Revenue",
                "text": "Revenue rose $500.00k to $7.50m.",
                "variance": 500000,
                "current": 7500000,
            },
            {
                "label": "EBITDA",
                "text": "EBITDA fell $120.00k.",
                "variance": -120000,
            },
        ],
        "causes": [
            {
                "label": "ARR vs revenue",
                "text": "Net new ARR was $400.00k while recognized revenue was $7.50m.",
                "amount": 400000,
            }
        ],
    }
    payload.update(overrides)
    return PeriodOverviewIn.model_validate(payload)


def test_pack_cause_paragraph_passes():
    section = _section()
    evidence = build_overview_evidence(section)
    paragraph = (
        "Revenue rose $500.00k while ARR grew $400.00k. "
        "Net new ARR was $400.00k while recognized revenue was $7.50m."
    )
    ok, reason = check_overview_paragraph(paragraph, evidence)
    assert ok, reason


def test_invented_customer_is_rejected_and_salvaged():
    section = _section()
    invented = analyze_period_overview(
        section,
        FakeClient("Revenue rose $500.00k because Acme Rockets came in at $999.00k."),
    )
    assert invented.status == "ai"
    assert invented.paragraph
    assert "Acme Rockets" not in invented.paragraph
    assert "Net new ARR" in invented.paragraph or "Revenue rose" in invented.paragraph


def test_invented_amount_is_salvaged():
    section = _section()
    result = analyze_period_overview(
        section,
        FakeClient("Revenue rose $999.99k and churn spiked for no listed reason."),
    )
    assert result.status == "ai"
    assert "$999.99k" not in result.paragraph
    evidence = build_overview_evidence(section)
    ok, reason = check_overview_paragraph(result.paragraph, evidence)
    assert ok, reason


def test_empty_packs_still_salvage_from_statement_facts():
    section = _section(causes=[])
    result = analyze_period_overview(section, None)
    assert result.status == "ai"
    assert result.paragraph
    assert "Revenue rose" in result.paragraph or "ARR grew" in result.paragraph


def test_attach_overview_packs_merges_server_causes(monkeypatch):
    packs = {
        "arr_vs_revenue_deferred": {
            "net_new_arr": 250000,
            "recognized_revenue": 7100000,
            "deferred_ending": 1200000,
        },
        "retention": {"gross_retention_rate": 0.92, "net_dollar_retention_rate": 1.05},
        "forecast_miss": {
            "events": [
                {
                    "customer": "Clearwater Software",
                    "amount": 120000,
                    "others": 0,
                    "others_amount": 0,
                    "outcome": "did not come in",
                }
            ]
        },
    }
    monkeypatch.setattr(
        "app.services.warehouse.close_insight_packs.load_insight_packs",
        lambda db, org, period: packs,
    )
    section = PeriodOverviewIn.model_validate(
        {
            "comparison": "Jul 2026 vs Jun 2026",
            "comparison_kind": "mom",
            "period": "2026-07",
            "organization_id": "8571e520-0687-4516-bdee-379f37c58c1f",
            "facts": [{"label": "Revenue", "text": "Revenue rose $10.00k.", "variance": 10000}],
            "causes": [],
        }
    )
    attached = attach_overview_packs(section, object())
    labels = {cause.label for cause in attached.causes}
    assert "ARR vs revenue" in labels
    assert "retention" in labels
    assert "forecast miss" in labels
    evidence = build_overview_evidence(attached)
    assert any(event.get("customer") == "Clearwater Software" for event in evidence["events"])
    paragraph = deterministic_overview_paragraph(evidence)
    assert "Clearwater Software" in paragraph
    ok, reason = check_overview_paragraph(paragraph, evidence)
    assert ok, reason


def test_qoq_without_packs_uses_facts_only():
    section = _section(
        comparison="Q2 2026 vs Q1 2026",
        comparison_kind="qoq",
        causes=[],
        lead="",
    )
    result = analyze_period_overview(section, None)
    assert result.status == "ai"
    assert "Revenue rose" in result.paragraph or "EBITDA" in result.paragraph


def test_rewrite_accepts_corrected_overview():
    section = _section()
    result = analyze_period_overview(
        section,
        SequenceClient(
            [
                "Revenue rose $999.99k because Mystery Co came in.",
                (
                    "Revenue rose $500.00k to $7.50m. "
                    "Net new ARR was $400.00k while recognized revenue was $7.50m."
                ),
            ]
        ),
    )
    assert result.status == "ai"
    assert "Mystery Co" not in result.paragraph
    assert "$500.00k" in result.paragraph or "Net new ARR" in result.paragraph
