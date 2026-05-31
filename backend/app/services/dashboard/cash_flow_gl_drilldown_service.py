"""Cash waterfall GL / workforce drilldown (click a bridge cell to see composition)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows, table_exists, value_any
from app.services.dashboard.schemas import CashFlowDrilldownLine, CashFlowDrilldownResponse
from app.services.management_pl.gl_hierarchy import GlEntry, classify_raw_gl_row, resolve_section_and_group
from app.services.management_pl.service import _gl_version_label, _load_gl_raw
from app.services.reporting.period_utils import combined_scenario_for_period, to_period
from app.services.reporting.validation_service import ValidationCheck, compare_values
from app.services.workforce import feeds, integration
from app.services.driver_forecast.common import month_range

CASH_DRILLDOWN_TYPES = frozenset(
    {
        "cash_collections",
        "payroll_cash_out",
        "commission_cash_out",
        "vendor_cash_out",
        "tax_cash_out",
        "capex",
        "financing",
    }
)

CASH_BALANCE_TYPES = frozenset({"beginning_cash", "ending_cash"})

VENDOR_GROUP_KEYWORDS = (
    "software",
    "contractors",
    "advertising",
    "legal",
    "insurance",
    "hosting",
    "infrastructure",
    "office",
    "travel",
    "events",
    "marketing",
    "audit",
    "recruiting",
    "third party",
    "payment processing",
    "customer support",
)


def _label(waterfall_type: str) -> str:
    return waterfall_type.replace("_", " ").title().replace("Arr", "ARR")


def _is_commission_entry(entry: GlEntry) -> bool:
    blob = f"{entry.account_name} {entry.account_group}".lower()
    return "commission" in blob


def _is_tax_entry(entry: GlEntry) -> bool:
    blob = f"{entry.account_name} {entry.account_group} {entry.expense_type}".lower()
    return any(token in blob for token in ("tax", "fringe", "fica", "withholding"))


def _is_capex_entry(entry: GlEntry) -> bool:
    blob = f"{entry.account_name} {entry.account_group}".lower()
    return any(token in blob for token in ("capex", "capital", "fixed asset", "equipment", "investment"))


def _is_financing_entry(entry: GlEntry) -> bool:
    blob = f"{entry.account_name} {entry.account_group}".lower()
    return any(token in blob for token in ("debt", "financ", "loan", "equity", "dividend", "interest"))


def _is_revenue_entry(entry: GlEntry) -> bool:
    section, _ = resolve_section_and_group(
        account_name=entry.account_name,
        account_group=entry.account_group,
        category="",
        expense_type=entry.expense_type,
        department=entry.department,
        amount=entry.amount,
    )
    return section == "revenue"


def _is_vendor_entry(entry: GlEntry, raw: dict) -> bool:
    if integration.is_payroll_gl_entry(entry) or _is_commission_entry(entry) or _is_tax_entry(entry):
        return False
    vendor_name = str(raw.get("vendor_name") or "").strip()
    vendor_id = str(raw.get("vendor_id") or "").strip()
    if vendor_name or vendor_id:
        return True
    ag = entry.account_group.lower()
    return any(keyword in ag for keyword in VENDOR_GROUP_KEYWORDS)


def gl_entry_matches(waterfall_type: str, entry: GlEntry, raw: dict) -> bool:
    if waterfall_type == "payroll_cash_out":
        return integration.is_payroll_gl_entry(entry) and not _is_commission_entry(entry)
    if waterfall_type == "commission_cash_out":
        return _is_commission_entry(entry)
    if waterfall_type == "tax_cash_out":
        return _is_tax_entry(entry)
    if waterfall_type == "capex":
        return _is_capex_entry(entry)
    if waterfall_type == "financing":
        return _is_financing_entry(entry)
    if waterfall_type == "vendor_cash_out":
        return _is_vendor_entry(entry, raw)
    if waterfall_type == "cash_collections":
        return _is_revenue_entry(entry)
    return False


def _signed_line_amount(waterfall_type: str, amount: Decimal) -> Decimal:
    if waterfall_type == "cash_collections":
        return abs(amount)
    return -abs(amount)


def _load_gl_entries_for_cell(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
    source_scenario: str,
) -> list[tuple[GlEntry, dict]]:
    matched: list[tuple[GlEntry, dict]] = []
    for raw in _load_gl_raw(session, organization_id):
        version = _gl_version_label(raw, default=source_scenario)
        if version.lower() != source_scenario.lower():
            continue
        period_key = to_period(str(raw.get("period") or ""))
        if period_key != period:
            continue
        entry = classify_raw_gl_row({**dict(raw), "version": version})
        if entry:
            matched.append((entry, dict(raw)))
    return matched


def _workforce_payroll_lines(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
    source_scenario: str,
) -> list[CashFlowDrilldownLine]:
    if not integration.workforce_source_present(session, organization_id, scenario=source_scenario):
        return []
    year, month = int(period[:4]), int(period[5:7])
    period_date = date(year, month, 1)
    rows = feeds.payroll_by_department(
        session,
        organization_id,
        scenario=source_scenario,
        start_period=period_date,
        end_period=period_date,
    )
    lines: list[CashFlowDrilldownLine] = []
    for row in rows:
        amount = value_any(row, "monthly_payroll_cost", "total_people_cost")
        if amount == 0:
            continue
        lines.append(
            CashFlowDrilldownLine(
                department=str(row.get("department") or ""),
                account_name="Workforce payroll",
                account_group="Payroll",
                amount=-abs(amount),
                source_table="workforce_derived",
                detail_type="workforce",
                notes=f"{row.get('headcount_fte', '')} FTE",
            )
        )
    return lines


def _invoice_collection_lines(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
) -> list[CashFlowDrilldownLine]:
    if not table_exists(session, "actual_invoices"):
        return []
    lines: list[CashFlowDrilldownLine] = []
    for raw in fetch_table_rows(session, "actual_invoices", organization_id):
        invoice_period = to_period(str(raw.get("invoice_period") or raw.get("period") or ""))
        if invoice_period != period:
            continue
        if str(raw.get("payment_status") or "").lower() != "paid":
            continue
        amount = value_any(raw, "invoice_amount", "amount")
        if amount == 0:
            continue
        lines.append(
            CashFlowDrilldownLine(
                department=str(raw.get("department") or "") or None,
                account_name=str(raw.get("customer_name") or raw.get("customer_id") or "Invoice collection"),
                account_group="Collections",
                vendor_name=str(raw.get("customer_name") or "") or None,
                amount=abs(amount),
                source_table="actual_invoices",
                detail_type="invoice",
            )
        )
    return lines


def _gl_lines_for_type(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
    source_scenario: str,
    waterfall_type: str,
) -> list[CashFlowDrilldownLine]:
    lines: list[CashFlowDrilldownLine] = []
    for entry, raw in _load_gl_entries_for_cell(
        session, organization_id, period=period, source_scenario=source_scenario
    ):
        if not gl_entry_matches(waterfall_type, entry, raw):
            continue
        lines.append(
            CashFlowDrilldownLine(
                account_number=entry.account_number or None,
                account_name=entry.account_name,
                account_group=entry.account_group,
                department=entry.department or None,
                vendor_name=str(raw.get("vendor_name") or "") or None,
                amount=_signed_line_amount(waterfall_type, entry.amount),
                source_table="gl_actuals",
                detail_type="gl",
            )
        )
    return lines


def cash_flow_drilldown_lines(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
    source_scenario: str,
    waterfall_type: str,
) -> list[CashFlowDrilldownLine]:
    if waterfall_type == "payroll_cash_out":
        workforce = _workforce_payroll_lines(
            session, organization_id, period=period, source_scenario=source_scenario
        )
        if workforce:
            return workforce
    if waterfall_type == "cash_collections":
        invoices = _invoice_collection_lines(session, organization_id, period=period)
        if invoices:
            return invoices
    return _gl_lines_for_type(
        session,
        organization_id,
        period=period,
        source_scenario=source_scenario,
        waterfall_type=waterfall_type,
    )


def cash_flow_gl_detail_counts(
    session: Session,
    organization_id: uuid.UUID,
    **params,
) -> dict[tuple[str, str, str], int]:
    start = to_period(params["start_period"])
    end = to_period(params["end_period"])
    scenario = params["scenario"]
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    counts: dict[tuple[str, str, str], int] = {}
    for period_date in month_range(date(sy, sm, 1), date(ey, em, 1)):
        period = period_date.strftime("%Y-%m")
        source_scenario = combined_scenario_for_period(period) if scenario == "Combined" else scenario
        for waterfall_type in CASH_DRILLDOWN_TYPES:
            lines = cash_flow_drilldown_lines(
                session,
                organization_id,
                period=period,
                source_scenario=source_scenario,
                waterfall_type=waterfall_type,
            )
            if lines:
                counts[(source_scenario, period, waterfall_type)] = len(lines)
    return counts


def cash_flow_drilldown(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    period: str,
    waterfall_type: str,
    expected_amount: Decimal | None = None,
) -> CashFlowDrilldownResponse:
    period_key = to_period(period)
    source_scenario = combined_scenario_for_period(period_key) if scenario == "Combined" else scenario

    if waterfall_type in CASH_BALANCE_TYPES:
        return CashFlowDrilldownResponse(
            organization_id=str(organization_id),
            scenario=scenario,
            source_scenario=source_scenario,
            period=period_key,
            waterfall_type=waterfall_type,
            line_item=_label(waterfall_type),
            lines=[],
            line_count=0,
            signed_total=Decimal("0"),
            expected_amount=expected_amount,
            drilldown_available=False,
            message="Beginning and ending cash are balance positions — select a movement line (collections, payroll, vendor, etc.) for GL detail.",
        )

    if waterfall_type not in CASH_DRILLDOWN_TYPES:
        return CashFlowDrilldownResponse(
            organization_id=str(organization_id),
            scenario=scenario,
            source_scenario=source_scenario,
            period=period_key,
            waterfall_type=waterfall_type,
            line_item=_label(waterfall_type),
            lines=[],
            line_count=0,
            signed_total=Decimal("0"),
            expected_amount=expected_amount,
            drilldown_available=False,
            message="No GL drilldown is defined for this cash bridge line.",
        )

    lines = cash_flow_drilldown_lines(
        session,
        organization_id,
        period=period_key,
        source_scenario=source_scenario,
        waterfall_type=waterfall_type,
    )
    source_tables = sorted({line.source_table for line in lines if line.source_table})
    signed_total = sum((line.amount for line in lines), Decimal("0"))

    validation: list[ValidationCheck] = []
    if expected_amount is not None and lines:
        validation.append(
            compare_values(
                scenario=source_scenario,
                period=period_key,
                validation_name="cash_cell_gl_lines_tie",
                expected_value=expected_amount,
                actual_value=signed_total,
                source_tables_used=source_tables or ["gl_actuals"],
            )
        )

    message = None
    if not lines:
        message = (
            "No GL detail rows matched this cell. Upload Actual_gl_detail.csv / Forecast_gl_detail.csv "
            "(or workforce headcount for payroll cash out, paid invoices for collections)."
        )

    return CashFlowDrilldownResponse(
        organization_id=str(organization_id),
        scenario=scenario,
        source_scenario=source_scenario,
        period=period_key,
        waterfall_type=waterfall_type,
        line_item=_label(waterfall_type),
        lines=lines,
        line_count=len(lines),
        signed_total=signed_total,
        expected_amount=expected_amount,
        drilldown_available=bool(lines),
        message=message,
        validation=validation,
        source_tables=source_tables,
    )
