"""Demo-data commission targets: closers from the new business plan, the renewal plan rate from the CSM targets."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import build_customer_history as bch  # noqa: E402
import build_workforce as wf  # noqa: E402

PLAN_HEADER = "organization_id,plan_id,role,eligible_opportunity_type,base_commission_rate\n"


def role(name: str):
    return next(r for r in wf.ROLES if r.role == name)


def test_closer_target_is_quota_times_the_plan_rate_and_csms_keep_the_role_target():
    rate = Decimal("0.1")
    assert wf.commission_target(role("Account Executive"), rate) == Decimal("80000.0")
    assert wf.commission_target(role("Senior Account Executive"), rate) == Decimal("110000.0")
    csm = role("Customer Success Manager")
    assert wf.commission_target(csm, rate) == csm.variable > 0
    assert wf.commission_target(role("Solutions Engineer"), rate) == 0


def test_new_business_rate_must_agree_across_versions(tmp_path):
    for v, rate in (("Actual", "0.1"), ("Budget", "0.1"), ("Forecast", "0.1")):
        (tmp_path / f"{v}_commission_plans.csv").write_text(
            PLAN_HEADER + f"o,PLAN-AE-NEW,AE,New Business,{rate}\no,PLAN-AM-EXP,AM,Expansion,0.06\n", encoding="utf-8")
    assert wf.new_business_rate(str(tmp_path)) == Decimal("0.1")
    (tmp_path / "Forecast_commission_plans.csv").write_text(
        PLAN_HEADER + "o,PLAN-AE-NEW,AE,New Business,0.12\n", encoding="utf-8")
    with pytest.raises(ValueError, match="disagree"):
        wf.new_business_rate(str(tmp_path))


def test_renewal_rate_pays_the_csm_targets_for_the_months_employed():
    employees = [
        {"role": "Customer Success Manager", "commission_target": "12000", "hire_date": "2020-01-06", "termination_date": ""},
        {"role": "Senior Customer Success Manager", "commission_target": "24000", "hire_date": "2026-04-01",
         "termination_date": ""},
        {"role": "Account Executive", "commission_target": "80000", "hire_date": "2020-01-06", "termination_date": ""},
    ]
    renewals = [{"renewal_period": "2026-02", "renewal_arr": "2000000"},
                {"renewal_period": "2026-05", "renewal_arr": "1000000"},
                {"renewal_period": "2026-07", "renewal_arr": "9000000"}]
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    # 12000 x 6/12 + 24000 x 3/12 = 12000 on 3,000,000 of renewals in the months
    assert bch.renewal_rate(employees, renewals, months) == Decimal("0.0040")
    with pytest.raises(ValueError, match="renewal plan rate"):
        bch.renewal_rate(employees[2:], renewals, months)
