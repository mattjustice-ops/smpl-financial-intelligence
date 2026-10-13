"""Payroll policies for planning: loaded policy rows and the register's realized 401(k) match."""

from __future__ import annotations

import pytest

from app.services.workforce.payroll_policies import payroll_policies_payload


def _policy(name: str, value: str, start: str = "2016-01", end: str | None = None, applies: str = "All") -> dict:
    return {"policy": name, "value": value, "effective_from": start, "effective_to": end, "applies_to": applies}


def _reg(period: str, wages: str, bonus: str, match: str) -> dict:
    return {"period": period, "regular_wages": wages, "bonus": bonus, "retirement_match": match}


POLICIES = [
    _policy("employer_payroll_tax_rate", "0.08"),
    _policy("health_benefits_monthly", "1200", "2026-01", "2026-12"),
    _policy("health_benefits_monthly", "1285", "2027-01", "2027-12"),
    _policy("merit_increase_pct", "0.035", "2016-04"),
    _policy("bonus_payout", "monthly"),
    _policy("", "9"),
]


def test_policy_rows_keep_numbers_terms_and_effective_dates() -> None:
    p = payroll_policies_payload(as_of_period="2026-06", policies=POLICIES, actual_register=[], forecast_register=[])
    assert p["version"] == "Forecast"
    by = {(r["policy"], r["effective_from"]): r for r in p["policies"]}
    assert len(p["policies"]) == 5, "rows without a policy name are dropped"
    assert by[("employer_payroll_tax_rate", "2016-01")]["value"] == 0.08
    assert by[("health_benefits_monthly", "2027-01")] == {
        "policy": "health_benefits_monthly", "value": 1285.0, "effective_from": "2027-01",
        "effective_to": "2027-12", "applies_to": "All"}
    assert by[("bonus_payout", "2016-01")]["value"] == "monthly"
    assert p["retirement_match_realized"] is None, "no register rows, no realized match"


def test_realized_match_uses_actual_register_through_close_and_forecast_after() -> None:
    actual = [_reg("2026-05", "1000", "100", "40"), _reg("2026-06", "1000", "0", "30"),
              _reg("2026-07", "999999", "0", "999"), _reg("2025-12", "5000", "0", "200")]
    forecast = [_reg("2026-06", "777777", "0", "1"), _reg("2026-07", "2000", "0", "50"), _reg("2026-08", "", "0", "9")]
    m = payroll_policies_payload(as_of_period="2026-06", policies=POLICIES, actual_register=actual,
                                 forecast_register=forecast)["retirement_match_realized"]
    assert m["match"] == 120.0 and m["base"] == 4100.0
    assert m["rate"] == pytest.approx(120 / 4100)
    assert m["span"] == "2026-05 to 2026-07" and m["months"] == 3
