"""Canonicalize workforce CSV layouts (simple CSVS / HRIS export formats)."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Optional

WORKFORCE_FILENAME_BASES: dict[str, str] = {
    "compensation_bands": "workforce_compensation_bands",
    "employees": "workforce_employees",
    "open_requisitions": "workforce_open_requisitions",
    "hiring_ramp_assumptions": "workforce_hiring_ramp_assumptions",
    "department_allocation_rules": "workforce_department_allocation_rules",
}

# Common filename typos / variants (stem without path, lowercased)
WORKFORCE_FILENAME_ALIASES: dict[str, str] = {
    "compensations_bands": "compensation_bands",
    "compensation_band": "compensation_bands",
    "compensationbands": "compensation_bands",
    "workforce_compensation_bands": "compensation_bands",
    "employee": "employees",
    "workforce_employees": "employees",
    "open_requisition": "open_requisitions",
    "workforce_open_requisitions": "open_requisitions",
    "hiring_ramp_assumption": "hiring_ramp_assumptions",
    "workforce_hiring_ramp_assumptions": "hiring_ramp_assumptions",
    "department_allocation_rule": "department_allocation_rules",
    "department_allocation": "department_allocation_rules",
    "workforce_department_allocation_rules": "department_allocation_rules",
}


def normalize_workforce_filename_base(stem: str) -> str | None:
    """Map uploaded filename stem to a workforce base key, if recognized."""
    key = stem.strip().lower().replace("-", "_")
    if key in WORKFORCE_FILENAME_ALIASES:
        key = WORKFORCE_FILENAME_ALIASES[key]
    if key in WORKFORCE_FILENAME_BASES:
        return key
    return None


def workforce_kind_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    from pathlib import Path

    stem = Path(filename).name.rsplit(".", 1)[0]
    stem_lower = stem.lower().replace("-", "_")
    if "_" in stem:
        prefix, rest = stem.split("_", 1)
        if prefix.lower() in {"actual", "actuals", "budget", "forecast"}:
            base = normalize_workforce_filename_base(rest.lower()) or rest.lower()
            mapped = WORKFORCE_FILENAME_BASES.get(base)
            if mapped:
                return mapped
    base = normalize_workforce_filename_base(stem_lower)
    if base:
        return WORKFORCE_FILENAME_BASES[base]
    return None

# Exact header sets from bundled simple CSVS exports
WORKFORCE_EXPANDED_HEADERS: dict[str, frozenset[str]] = {
    "workforce_compensation_bands": frozenset(
        {
            "department",
            "role",
            "level",
            "salary_midpoint",
            "salary_low",
            "salary_high",
            "variable_comp_target",
            "equity_sbc_annual",
            "benefits_load_pct",
            "fully_loaded_cash_cost_midpoint",
            "fully_loaded_gaap_cost_midpoint",
            "quota_carrying",
            "annual_quota_arr",
            "productivity_ramp_months",
        }
    ),
    "workforce_employees": frozenset(
        {
            "employee_id",
            "employee_name",
            "scenario",
            "department",
            "sub_department",
            "role",
            "level",
            "region",
            "manager",
            "employment_status",
            "hire_date",
            "termination_date",
            "base_salary",
            "variable_comp",
            "commission_target",
            "equity_sbc_annual",
            "benefits_load_pct",
            "fully_loaded_cash_cost",
            "fully_loaded_gaap_cost",
            "quota_carrying",
            "annual_quota_arr",
            "productivity_ramp_months",
            "remote_flag",
            "source",
        }
    ),
    "workforce_hiring_ramp_assumptions": frozenset(
        {"ramp_months", "month_after_start", "productivity_pct", "applies_to"}
    ),
    "workforce_department_allocation_rules": frozenset(
        {
            "department",
            "statement_category",
            "sub_department_mapping",
            "allocation_description",
            "allocation_pct",
            "management_view_include",
            "accounting_view_include",
        }
    ),
    "workforce_open_requisitions": frozenset(
        {
            "req_id",
            "scenario",
            "department",
            "sub_department",
            "role",
            "level",
            "status",
            "approved_flag",
            "priority",
            "replacement_vs_new",
            "hiring_manager",
            "recruiter",
            "target_hire_date",
            "planned_start_date",
            "scenario_start_date",
            "scenario_delay_months",
            "source",
        }
    ),
}

WORKFORCE_SUBSET_SIGNATURES: dict[str, frozenset[str]] = {
    "workforce_compensation_bands": frozenset({"department", "role", "level", "salary_midpoint"}),
    "workforce_employees": frozenset({"employee_id", "department", "role", "base_salary"}),
    "workforce_hiring_ramp_assumptions": frozenset({"ramp_months", "month_after_start", "productivity_pct"}),
    "workforce_department_allocation_rules": frozenset({"department", "statement_category", "allocation_pct"}),
    "workforce_open_requisitions": frozenset({"req_id", "department", "role", "planned_start_date"}),
}

# backend/demo_data/*.csv warehouse-native headers (already match SQLAlchemy models)
WORKFORCE_WAREHOUSE_SIGNATURES: dict[str, frozenset[str]] = {
    "workforce_compensation_bands": frozenset({"department", "role", "level", "base_salary_annual"}),
    "workforce_employees": frozenset({"employee_id", "department", "role", "salary_annual"}),
    "workforce_hiring_ramp_assumptions": frozenset({"department", "role", "month_offset", "productivity_pct"}),
    "workforce_department_allocation_rules": frozenset({"rule_id", "department", "pnl_line", "allocation_pct"}),
}


def detect_workforce_kind(headers: frozenset[str]) -> Optional[str]:
    for kind, expected in WORKFORCE_EXPANDED_HEADERS.items():
        if headers == expected:
            return kind
    matches = [kind for kind, sig in WORKFORCE_SUBSET_SIGNATURES.items() if sig <= headers]
    matches.extend(kind for kind, sig in WORKFORCE_WAREHOUSE_SIGNATURES.items() if sig <= headers)
    unique = list(dict.fromkeys(matches))
    if len(unique) == 1:
        return unique[0]
    return None


def _yes(value: Any) -> bool:
    return str(value or "").strip().lower() in {"yes", "y", "true", "1"}


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")[:64]


def _statement_to_pnl_line(statement_category: str) -> str:
    blob = statement_category.strip().lower()
    if "sales" in blob and "marketing" in blob:
        return "sales_and_marketing"
    if "research" in blob or "r&d" in blob or blob == "rd":
        return "research_and_development"
    if "general" in blob or "g&a" in blob or blob == "ga":
        return "general_and_administrative"
    if "cost" in blob or "cogs" in blob:
        return "cost_of_revenue"
    return _slug(statement_category)


def expand_hiring_ramp_rows(rows: list[dict[str, Any]], *, version: Optional[str] = None) -> list[dict[str, Any]]:
    """Map ramp_months curves into workforce_hiring_ramp_assumptions rows."""
    out: list[dict[str, Any]] = []
    for raw in rows:
        ramp_months = str(raw.get("ramp_months", "")).strip()
        month_after = int(str(raw.get("month_after_start", "1")).strip() or "1")
        out.append(
            {
                "version": version or "Forecast",
                "department": "*",
                "role": "*",
                "level": ramp_months,
                "month_offset": max(0, month_after - 1),
                "productivity_pct": raw.get("productivity_pct"),
                "notes": raw.get("applies_to"),
            }
        )
    return out


def canonicalize_workforce_row(
    kind: str,
    row: dict[str, Any],
    *,
    version_hint: Optional[str] = None,
) -> dict[str, Any]:
    out = dict(row)
    version = out.get("version") or out.get("scenario") or version_hint or "Forecast"

    if kind == "workforce_compensation_bands":
        if out.get("base_salary_annual") is not None and out.get("salary_midpoint") is None:
            return {
                "version": version,
                "department": out.get("department"),
                "role": out.get("role"),
                "level": out.get("level") or "",
                "region": out.get("region") or "",
                "base_salary_annual": out.get("base_salary_annual"),
                "bonus_target_pct": out.get("bonus_target_pct"),
                "commission_annual": out.get("commission_annual"),
                "equity_sbc_annual": out.get("equity_sbc_annual"),
                "benefits_load_pct": out.get("benefits_load_pct"),
                "default_quota_capacity_arr": out.get("default_quota_capacity_arr"),
            }
        midpoint = out.get("salary_midpoint") or out.get("base_salary_annual")
        variable = out.get("variable_comp_target")
        dept = str(out.get("department", ""))
        is_sales = dept.lower() == "sales"
        return {
            "version": version,
            "department": dept,
            "role": out.get("role"),
            "level": out.get("level") or "",
            "region": out.get("region") or "",
            "base_salary_annual": midpoint,
            "bonus_target_pct": None if is_sales else (Decimal(str(variable)) / Decimal(str(midpoint)) if midpoint and variable else None),
            "commission_annual": variable if is_sales else out.get("commission_annual"),
            "equity_sbc_annual": out.get("equity_sbc_annual"),
            "benefits_load_pct": out.get("benefits_load_pct"),
            "default_quota_capacity_arr": out.get("annual_quota_arr") if _yes(out.get("quota_carrying")) else Decimal("0"),
        }

    if kind == "workforce_employees":
        if out.get("salary_annual") is not None and out.get("base_salary") is None:
            out = {**out, "version": version}
            return out
        status = str(out.get("employment_status") or out.get("status") or "Active")
        return {
            "version": version,
            "employee_id": out.get("employee_id"),
            "department": out.get("department"),
            "sub_department": out.get("sub_department"),
            "role": out.get("role"),
            "level": out.get("level"),
            "region": out.get("region"),
            "hire_date": out.get("hire_date"),
            "termination_date": out.get("termination_date"),
            "employment_status": status,
            "salary_annual": out.get("salary_annual") or out.get("base_salary"),
            "bonus_annual": out.get("bonus_annual") or (None if out.get("commission_target") else out.get("variable_comp")),
            "commission_annual": out.get("commission_annual") or out.get("commission_target"),
            "equity_sbc_annual": out.get("equity_sbc_annual"),
            "benefits_load_pct": out.get("benefits_load_pct"),
            "quota_capacity_arr": out.get("quota_capacity_arr")
            or (out.get("annual_quota_arr") if _yes(out.get("quota_carrying")) else None),
            "months_to_full_productivity": _as_int(out.get("months_to_full_productivity") or out.get("productivity_ramp_months")),
        }

    if kind == "workforce_open_requisitions":
        approved = out.get("approved_status")
        if approved is None:
            flag = str(out.get("approved_flag", "")).strip().lower()
            approved = "Approved" if flag in {"yes", "y", "true", "1"} else str(out.get("status") or "Open")
        req_type = str(out.get("requisition_type") or out.get("replacement_vs_new") or "new").lower()
        if req_type.startswith("repl"):
            req_type = "replacement"
        else:
            req_type = "new"
        return {
            "version": version,
            "req_id": out.get("req_id"),
            "role": out.get("role"),
            "department": out.get("department"),
            "sub_department": out.get("sub_department"),
            "hiring_manager": out.get("hiring_manager"),
            "target_hire_date": out.get("target_hire_date"),
            "planned_start_date": out.get("planned_start_date"),
            "priority": out.get("priority"),
            "approved_status": approved,
            "requisition_type": req_type,
            "level": out.get("level"),
            "region": out.get("region"),
            "salary_annual_override": out.get("salary_annual_override"),
            "quota_capacity_arr_override": out.get("quota_capacity_arr_override"),
        }

    if kind == "workforce_hiring_ramp_assumptions":
        if out.get("month_offset") is not None and out.get("ramp_months") is None:
            return {
                "version": version,
                "department": out.get("department", "*"),
                "role": out.get("role", "*"),
                "level": str(out.get("level", "")),
                "month_offset": int(out.get("month_offset", 0)),
                "productivity_pct": out.get("productivity_pct"),
                "notes": out.get("notes"),
            }
        return {
            "version": version,
            "department": out.get("department", "*"),
            "role": out.get("role", "*"),
            "level": str(out.get("level", "")),
            "month_offset": int(out.get("month_offset", 0)),
            "productivity_pct": out.get("productivity_pct"),
            "notes": out.get("notes"),
        }

    if kind == "workforce_department_allocation_rules":
        if out.get("pnl_line") is not None and out.get("statement_category") is None:
            return {
                "version": version,
                "rule_id": out.get("rule_id"),
                "department": out.get("department"),
                "pnl_line": out.get("pnl_line"),
                "allocation_pct": out.get("allocation_pct"),
                "effective_start": out.get("effective_start"),
                "effective_end": out.get("effective_end"),
                "notes": out.get("notes"),
            }
        dept = str(out.get("department", ""))
        statement = str(out.get("statement_category") or out.get("pnl_line") or "")
        rule_id = out.get("rule_id") or f"{_slug(dept)}_{_slug(statement)}"
        return {
            "version": version,
            "rule_id": rule_id,
            "department": dept,
            "pnl_line": _statement_to_pnl_line(statement),
            "allocation_pct": out.get("allocation_pct"),
            "effective_start": out.get("effective_start"),
            "effective_end": out.get("effective_end"),
            "notes": out.get("allocation_description") or out.get("notes"),
        }

    return out


def preprocess_workforce_upload(
    kind: str,
    headers: list[str],
    rows: list[dict[str, Any]],
    *,
    version_hint: Optional[str] = None,
) -> list[dict[str, Any]]:
    hs = frozenset(h.strip() for h in headers if h.strip())
    if kind == "workforce_hiring_ramp_assumptions" and "ramp_months" in hs:
        expanded = expand_hiring_ramp_rows(rows, version=version_hint)
        return [canonicalize_workforce_row(kind, r, version_hint=version_hint) for r in expanded]
    return [canonicalize_workforce_row(kind, dict(r), version_hint=version_hint) for r in rows]
