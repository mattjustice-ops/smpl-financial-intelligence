"""The company profile the commentary and exports read: recorded fields only, nothing assumed."""

from __future__ import annotations

import pytest

from app.services.company_profile import (
    CompanyProfileRejected,
    company_context_for_prompt,
    company_name,
    normalize_profile,
    profile_record,
)
from app.services.reporting.export.mda_variance_package import _stamp, export_filename


def test_the_profile_keeps_known_fields_trimmed_and_drops_the_rest():
    fields = normalize_profile({
        "display_name": "  Acme Analytics ",
        "industry": "",
        "strategic_priorities": ["Grow enterprise ARR", " ", "Hold cash"],
        "competitors": [{"name": "Northwind", "positioning": "Mid-market"}, "Contoso", {"positioning": "no name"}],
        "cash_floor": "$12,500,000",
        "currency": "usd",
        "made_up": "ignored",
    })
    assert fields == {
        "display_name": "Acme Analytics",
        "currency": "USD",
        "strategic_priorities": ["Grow enterprise ARR", "Hold cash"],
        "competitors": [{"name": "Northwind", "positioning": "Mid-market"}, {"name": "Contoso", "positioning": ""}],
        "cash_floor": "12500000.00",
    }


def test_a_cash_floor_that_is_not_an_amount_is_rejected():
    with pytest.raises(CompanyProfileRejected):
        normalize_profile({"cash_floor": "ten million"})


def test_the_company_name_is_the_display_name_else_the_organization_name():
    assert company_name(profile_record("Acme Inc", {"display_name": "Acme Analytics"})) == "Acme Analytics"
    assert company_name(profile_record("Acme Inc", {})) == "Acme Inc"
    assert company_name(profile_record(None, {})) == ""


def test_the_prompt_states_what_is_recorded_and_names_what_is_not():
    profile = profile_record("Acme Inc", {"industry": "Logistics software", "cash_floor": 5_000_000, "currency": "USD"})
    text = company_context_for_prompt(profile)
    assert "Company: Acme Inc" in text
    assert "Industry: Logistics software" in text
    assert "Cash floor: 5000000.00 USD" in text
    assert "Not provided by the company:" in text and "Stage" in text and "Competitors" in text
    assert "Do not assume" in text
    assert "SMPL" not in text and "Series B" not in text


def test_a_company_with_nothing_recorded_gets_no_invented_context():
    text = company_context_for_prompt(profile_record(None, {}))
    assert "Company: not provided" in text
    assert "Cash floor:" not in text.split("Not provided")[0]


def test_the_mda_stamp_and_file_carry_the_company_not_smpl():
    package = {"comparisons": []}
    stamp = _stamp(package, "2026-07", "Acme Analytics", "2026-08-05T00:00:00Z")
    assert stamp["packageId"] == "MDA-ACME_ANALYTICS-2026-07-001"
    assert stamp["snapshot"] == "SNAP-ACME_ANALYTICS-2026-07"
    assert stamp["entityName"] == "Acme Analytics"
    assert export_filename({"stamp": stamp}) == "Acme_Analytics_MDA_Variance_Commentary_2026-07_DRAFT.xlsx"
