"""Demo-data sales team: quota types, deal owners and CSM accounts (scripts/demo_data)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import build_v5_dataset as v5  # noqa: E402
import build_workforce as wf  # noqa: E402
import sales_team as st  # noqa: E402


def rep(emp: str, role: str, region: str, ramped: str) -> dict:
    return {"employee_id": emp, "role": role, "region": region, "ramped_monthly_quota_arr": ramped}


def deal(oid: str, period: str, amount: str, kind: str = "New Business", status: str = "Closed Won") -> dict:
    return {"opportunity_id": oid, "period": f"{period}-15", "region": "South", "opportunity_type": kind,
            "close_status": status, "amount_arr": amount, "weighted_arr": amount}


def test_quota_type_by_role_and_workforce_roles_carry_quota_exactly_when_typed():
    assert st.quota_type("Account Executive") == "Bookings ARR"
    assert st.quota_type("Sales Development Rep") == "Pipeline ARR"
    assert st.quota_type("Customer Success Manager") == "Expansion ARR"
    assert st.quota_type("Senior Customer Success Manager") == "Expansion ARR"
    assert st.quota_type("Sales Enablement Manager") == "Non-Quota"
    for role in wf.ROLES:
        assert (wf.carrying(role) == "Yes") == (st.quota_type(role.role) != "Non-Quota"), role.role
    assert {r.role for r in wf.ROLES if wf.carrying(r) == "Yes"} >= st.CSM_ROLES


def test_new_business_skips_a_ramping_rep_the_deal_would_overload():
    roster = {"by_period": {"2026-05": [rep("EMP-1", "Account Executive", "South", "100000"),
                                        rep("EMP-2", "Account Executive", "South", "10000")]}}
    assert v5.assign_owners([deal("D1", "2026-05", "150000")], roster) == {"D1": "EMP-1"}


def test_new_business_balances_on_year_to_date_attainment():
    roster = {"by_period": {"2026-01": [rep("EMP-1", "Account Executive", "South", "100000")],
                            "2026-02": [rep("EMP-1", "Account Executive", "South", "100000"),
                                        rep("EMP-2", "Senior Account Executive", "South", "100000")]}}
    owner = v5.assign_owners([deal("D1", "2026-01", "300000"), deal("D2", "2026-02", "100000")], roster)
    assert owner == {"D1": "EMP-1", "D2": "EMP-2"}


def test_other_deals_go_round_robin_and_never_to_reps_without_ramped_quota():
    roster = {"by_period": {"2026-03": [rep("EMP-1", "Account Executive", "South", "50000"),
                                        rep("EMP-2", "Account Executive", "South", "50000"),
                                        rep("EMP-3", "Account Executive", "South", "0"),
                                        rep("EMP-4", "Customer Success Manager", "South", "50000")]}}
    opps = [deal(f"D{i}", "2026-03", "1000", kind="Expansion") for i in range(4)]
    assert list(v5.assign_owners(opps, roster).values()) == ["EMP-1", "EMP-2", "EMP-1", "EMP-2"]


def test_customer_gets_the_csm_on_staff_when_it_first_expands_or_renews():
    team = [{"employee_id": "EMP-10", "role": "Customer Success Manager", "region": "South",
             "hire_date": "2020-01-06", "termination_date": ""},
            {"employee_id": "EMP-11", "role": "Senior Customer Success Manager", "region": "South",
             "hire_date": "2026-03-16", "termination_date": ""}]
    due = [{"customer_id": "CUST-1", "period": "2026-08"}, {"customer_id": "CUST-2", "period": "2026-04"},
           {"customer_id": "CUST-1", "period": "2026-01"}]
    assert st.assign_csms(due, team, lambda c: "South", {}) == {"CUST-1": "EMP-10", "CUST-2": "EMP-11"}


def test_customer_first_seen_expanding_goes_to_the_csm_left_lowest_against_quota():
    team = [{"employee_id": f"EMP-{i}", "role": "Customer Success Manager", "region": "South",
             "hire_date": "2020-01-06", "termination_date": "", "annual_quota_arr": "600000"} for i in (10, 11)]
    due = [{"customer_id": "CUST-1", "period": "2026-01", "expansion_arr": Decimal("150000")},
           {"customer_id": "CUST-2", "period": "2026-02"},
           {"customer_id": "CUST-1", "period": "2026-03", "expansion_arr": Decimal("100000")},
           {"customer_id": "CUST-3", "period": "2026-04", "expansion_arr": Decimal("120000")},
           {"customer_id": "CUST-4", "period": "2026-05", "expansion_arr": Decimal("90000")}]
    assert st.assign_csms(due, team, lambda c: "South", {}) == {
        "CUST-1": "EMP-10", "CUST-2": "EMP-11", "CUST-3": "EMP-11", "CUST-4": "EMP-11"}
    assert st.ytd_quota(team[0], "2026-05") == Decimal("250000")
