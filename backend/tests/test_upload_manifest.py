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
    for oid in ("vendor_bill", "vendor_payment", "ap_aging", "fixed_asset", "debt_schedule", "prepaid_schedule",
                "sbc_schedule", "commission_payout"):
        assert by_object[oid] > 0, oid


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
    base = {"7.30": "by_employee", "7.31": "yes", "7.32": "yes", "7.35": "all", "7.36": "yes"}
    assert _normalization_status({**base, "7.33": "no"})["data_sources"]["resolved"]
    pending = _normalization_status({**base, "7.33": "yes"})["data_sources"]
    assert pending["unresolved_questions"] == ["7.34"]
    assert _normalization_status({**base, "7.33": "yes", "7.34": "net_30"})["data_sources"]["resolved"]


def test_data_source_answers_validate():
    assert validate_answers({"7.30": "by_department", "7.33": "yes", "7.34": "mixed", "7.35": "some"}) == []
    assert validate_answers({"7.34": "net_90"})


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
