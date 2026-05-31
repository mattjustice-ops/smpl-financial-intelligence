"""Workforce CSV detection and canonicalization."""

from __future__ import annotations

from app.services.demo_csv.detector import detect_csv_kind
from app.services.demo_csv.workforce_csv import canonicalize_workforce_row, expand_hiring_ramp_rows


def test_expand_hiring_ramp_rows() -> None:
    rows = expand_hiring_ramp_rows(
        [{"ramp_months": "4", "month_after_start": "2", "productivity_pct": "0.25", "applies_to": "test"}]
    )
    assert rows[0]["department"] == "*"
    assert rows[0]["level"] == "4"
    assert rows[0]["month_offset"] == 1
    assert rows[0]["productivity_pct"] == "0.25"


def test_canonicalize_compensation_band() -> None:
    row = canonicalize_workforce_row(
        "workforce_compensation_bands",
        {
            "department": "Sales",
            "role": "Account Executive",
            "level": "L4",
            "salary_midpoint": "125000",
            "variable_comp_target": "55000",
            "equity_sbc_annual": "12000",
            "benefits_load_pct": "0.18",
            "quota_carrying": "Yes",
            "annual_quota_arr": "800000",
        },
        version_hint="Forecast",
    )
    assert row["base_salary_annual"] == "125000"
    assert row["commission_annual"] == "55000"
    assert row["default_quota_capacity_arr"] == "800000"


def test_canonicalize_employee_scenario_column() -> None:
    row = canonicalize_workforce_row(
        "workforce_employees",
        {
            "employee_id": "EMP-1",
            "scenario": "Forecast",
            "department": "Sales",
            "role": "AE",
            "base_salary": "100000",
            "commission_target": "50000",
            "employment_status": "Active",
            "productivity_ramp_months": "4",
        },
    )
    assert row["version"] == "Forecast"
    assert row["salary_annual"] == "100000"
    assert row["months_to_full_productivity"] == 4


def test_demo_data_comp_bands_detected() -> None:
    from pathlib import Path

    from app.services.demo_csv.loader import parse_csv
    from app.services.demo_csv.workforce_csv import workforce_kind_from_filename

    path = Path(__file__).resolve().parents[1] / "demo_data" / "workforce_compensation_bands.csv"
    headers, _ = parse_csv(path.read_bytes())
    assert workforce_kind_from_filename(path.name) == "workforce_compensation_bands"
    assert detect_csv_kind(headers) == "workforce_compensation_bands"


def test_canonicalize_warehouse_native_comp_band() -> None:
    row = canonicalize_workforce_row(
        "workforce_compensation_bands",
        {
            "version": "Forecast",
            "department": "Sales",
            "role": "Account Executive",
            "level": "L3",
            "region": "US",
            "base_salary_annual": "125000",
            "bonus_target_pct": "0.15",
            "commission_annual": "90000",
            "default_quota_capacity_arr": "900000",
        },
    )
    assert row["bonus_target_pct"] == "0.15"
    assert row["default_quota_capacity_arr"] == "900000"
