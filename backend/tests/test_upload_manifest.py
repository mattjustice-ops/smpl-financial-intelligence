"""Upload manifest generated from the readiness registry."""

from __future__ import annotations

import csv
import importlib.util
from collections import Counter
from pathlib import Path

from app.services.readiness.engine import _normalization_status, validate_answers
from app.services.readiness.manifest import MANIFEST_COLUMNS, check_files, classify, manifest_rows
from app.services.readiness.registry import ALL_QUESTIONS, OBJECTS, VERSIONS

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "write_upload_manifest.py"
_spec = importlib.util.spec_from_file_location("write_upload_manifest", _SCRIPT)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
write_manifest = _module.main


def test_every_manifest_file_has_a_loader_target():
    rows = manifest_rows()
    assert rows
    assert [r["file_name"] for r in rows if not r["target_table"]] == []
    assert all(set(r) == set(MANIFEST_COLUMNS) for r in rows)


def test_file_names_and_load_sequence_are_unique():
    rows = manifest_rows()
    assert [n for n, c in Counter(r["file_name"].lower() for r in rows).items() if c > 1] == []
    assert [r["load_sequence"] for r in rows] == [f"{i:03d}" for i in range(1, len(rows) + 1)]


def test_dimensions_load_before_ledgers_and_statements_last():
    order = [r["object_id"] for r in manifest_rows()]
    assert order.index("gl_account") < order.index("journal_entry") < order.index("income_statement")
    assert order.index("employee") < order.index("payroll_line")
    assert order[-1] == "cash_flow_statement"


def test_object_questions_exist():
    assert [o.id for o in OBJECTS.values() if o.question and o.question not in ALL_QUESTIONS] == []


def test_payroll_register_and_policies_listed_for_every_version():
    names = {r["file_name"] for r in manifest_rows()}
    for base in ("payroll_register", "payroll_policies", "Employees"):
        assert {f"{v}_{base}.csv" for v in VERSIONS} <= names


def test_ap_and_schedule_objects_are_declared_for_onboarding():
    by_object = Counter(r["object_id"] for r in manifest_rows())
    for oid in ("vendor", "vendor_bill", "vendor_payment", "ap_aging", "fixed_asset", "debt_schedule",
                "prepaid_schedule", "sbc_schedule", "commission_payout", "vendor_spend_plan", "accrued_expenses",
                "lease_schedule"):
        assert by_object[oid] > 0, oid
    names = {r["file_name"] for r in manifest_rows()}
    assert {f"{v}_{base}.csv" for v in VERSIONS for base in ("accrued_expenses_rollforward",
                                                              "operating_lease_schedule")} <= names
    assert "Actual_accrued_expenses_detail.csv" in names and "Budget_accrued_expenses_detail.csv" not in names


def test_ap_subledger_is_actual_only_and_plans_use_the_spend_plan():
    rows = manifest_rows()
    names = {r["file_name"] for r in rows}
    for base in ("vendor_master", "vendor_bills", "vendor_payments", "AP_Aging"):
        assert f"Actual_{base}.csv" in names
        assert not {f"Budget_{base}.csv", f"Forecast_{base}.csv"} & names, base
    assert {"Budget_vendor_spend_plan.csv", "Forecast_vendor_spend_plan.csv"} <= names
    assert not [n for n in names if "vendor_accrual_payment_schedule" in n]
    order = [r["object_id"] for r in rows]
    assert order.index("vendor") < order.index("vendor_bill") < order.index("vendor_payment") < order.index("ap_aging")


def test_collections_files_are_declared():
    rows = manifest_rows()
    names = {r["file_name"] for r in rows}
    assert {f"{v}_allowance_for_doubtful_accounts.csv" for v in VERSIONS} <= names
    for base in ("customer_payments", "AR_Aging", "collections_cases", "collections_activity", "commission_clawbacks"):
        assert f"Actual_{base}.csv" in names
        assert not {f"Budget_{base}.csv", f"Forecast_{base}.csv"} & names, base
    order = [r["object_id"] for r in rows]
    assert order.index("invoice") < order.index("customer_payment") < order.index("ar_aging")
    by_file = {r["file_name"]: r for r in rows}
    assert by_file["Actual_customer_payments.csv"]["question"] == "7.37"
    assert by_file["Actual_collections_cases.csv"]["question"] == "7.38"
    assert by_file["Actual_commission_clawbacks.csv"]["object_id"] == "commission_payout"


def test_shared_workforce_inputs_carry_no_version_prefix():
    shared = [r for r in manifest_rows() if r["dataset_type"] == "Shared"]
    assert {r["file_name"] for r in shared} == {
        "Compensation_Bands.csv", "Hiring_Ramp_Assumptions.csv", "Department_Allocation_Rules.csv"}
    assert all(r["target_table"].startswith("workforce_") for r in shared)


def test_classify():
    assert classify("Actual_payroll_register.csv") == "payroll_line"
    assert classify("forecast_PAYROLL_REGISTER.csv") == "payroll_line"
    assert classify("Compensation_Bands.csv") == "hiring_plan_input"
    assert classify("Budget_gl_detail.csv") == "budget_line"
    assert classify("Actual_vendor_master.csv") == "vendor"
    assert classify("Forecast_vendor_spend_plan.csv") == "vendor_spend_plan"
    assert classify("Budget_AP_Aging.csv") is None
    assert classify("Forecast_operating_lease_schedule.csv") == "lease_schedule"
    assert classify("Actual_accrued_expenses_detail.csv") == "accrued_expenses"
    assert classify("Actual_AR_Aging.csv") == "ar_aging"
    assert classify("Budget_allowance_for_doubtful_accounts.csv") == "allowance_for_doubtful_accounts"
    assert classify("Actual_collections_activity.csv") == "collections_case"
    assert classify("Forecast_customer_payments.csv") is None
    assert classify("Actual_unknown_export.csv") is None


def test_check_files_reports_undeclared_duplicates_reference_and_missing():
    result = check_files([
        "Actual_payroll_register.csv",
        "dir_a/Actual_gl_detail.csv",
        "dir_b/Actual_gl_detail.csv",
        "Workforce_Scenario_Assumptions.csv",
        "Actual_Validation_Summary.csv",
        "gl_balance_sheet_check.csv",
        "build_log.csv",
    ])
    assert result["mapped"] == {"Actual_payroll_register.csv": "payroll_line", "Actual_gl_detail.csv": "journal_entry"}
    assert result["duplicates"] == ["actual_gl_detail.csv"]
    assert result["undeclared"] == ["Workforce_Scenario_Assumptions.csv"]
    assert result["reference"] == ["Actual_Validation_Summary.csv", "build_log.csv", "gl_balance_sheet_check.csv"]
    missing = result["missing"]
    assert "Budget_payroll_register.csv" in missing["payroll_line"]
    assert "Actual_payroll_register.csv" not in missing["payroll_line"]


def test_vendor_terms_only_required_when_ap_subledger_exportable():
    base = {"7.30": "by_employee", "7.31": "yes", "7.32": "yes", "7.35": "all", "7.36": "yes", "7.37": "yes",
            "7.38": "no", "7.39": "yes", "7.40": "no"}
    assert _normalization_status({**base, "7.33": "no"})["data_sources"]["resolved"]
    pending = _normalization_status({**base, "7.33": "yes"})["data_sources"]
    assert pending["unresolved_questions"] == ["7.34"]
    assert _normalization_status({**base, "7.33": "yes", "7.34": "net_30"})["data_sources"]["resolved"]


def test_data_source_answers_validate():
    assert validate_answers({"7.30": "by_department", "7.33": "yes", "7.34": "mixed", "7.35": "some"}) == []
    assert validate_answers({"7.34": "net_90"})
    assert validate_answers({"7.37": "yes", "7.38": "no"}) == []
    assert validate_answers({"7.38": "sometimes"})
    assert validate_answers({"7.39": "yes", "7.40": "no"}) == []


def test_customer_bucket_questions_and_files():
    assert all(q.default is None or q.default in q.choices for q in ALL_QUESTIONS.values())
    assert (ALL_QUESTIONS["4.10"].default, ALL_QUESTIONS["4.12"].default) == ("6", "12")
    assert validate_answers({"4.10": "6", "4.11": "removes_arr", "4.12": "12"}) == []
    assert validate_answers({"4.12": "9"})
    # Defaults are shown, not assumed: the gate waits for explicit answers.
    status = _normalization_status({"4.10": "6", "4.11": "removes_arr"})["customer_returns"]
    assert status["unresolved_questions"] == ["4.12"]
    assert _normalization_status({"4.10": "6", "4.11": "removes_arr", "4.12": "12"})["customer_returns"]["resolved"]
    by_file = {r["file_name"]: r for r in manifest_rows()}
    for v in VERSIONS:
        assert by_file[f"{v}_customers.csv"]["question"] == "7.39"
        assert by_file[f"{v}_customer_arr_history.csv"]["question"] == "7.40"


def test_script_writes_manifest_and_fails_on_undeclared_files(tmp_path):
    data = tmp_path / "dataset"
    data.mkdir()
    for name in ("Actual_payroll_register.csv", "Workforce_Scenario_Assumptions.csv"):
        (data / name).write_text("a\n1\n", encoding="utf-8")
    out = tmp_path / "master_upload_order.csv"

    assert write_manifest([str(out), str(data)]) == 1
    assert write_manifest([str(out), str(data), "--allow-undeclared"]) == 0
    with open(out, newline="", encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    assert written == manifest_rows()
