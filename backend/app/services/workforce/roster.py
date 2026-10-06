"""
Employee roster for workforce plans.

Reads the loaded ``{version}_employees`` table (Employees CSV); falls back to the
``workforce_employees`` upload table only when no loaded roster exists for the version.
The roster supplies head counts, quota and the roster cost used in the GL payroll check;
payroll dollars come from the GL (see ``gl_payroll``).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.workforce import WorkforceEmployee
from app.services.dashboard.query_utils import fetch_table_rows, table_exists
from app.services.workforce.constants import ACTIVE_EMPLOYMENT_STATUSES

logger = logging.getLogger(__name__)

ROSTER_TABLES: dict[str, str] = {
    "Actual": "actual_employees",
    "Budget": "budget_employees",
    "Forecast": "forecast_employees",
}
UPLOAD_ROSTER_TABLE = WorkforceEmployee.__tablename__
PLANNED_STATUSES: frozenset[str] = frozenset({"planned"})


@dataclass
class RosterEmployee:
    employee_id: str
    department: str
    role: str
    level: str | None
    region: str | None
    employment_status: str
    hire_date: date | None
    termination_date: date | None
    salary_annual: Decimal | None
    bonus_annual: Decimal | None
    commission_annual: Decimal | None
    equity_sbc_annual: Decimal | None
    benefits_load_pct: Decimal | None
    quota_capacity_arr: Decimal | None
    productivity_ramp_pct: Decimal | None
    months_to_full_productivity: int | None
    annual_cash_cost: Decimal

    @property
    def planned(self) -> bool:
        return self.employment_status.strip().lower() in PLANNED_STATUSES

    @property
    def counted(self) -> bool:
        status = self.employment_status.strip().lower()
        return status in ACTIVE_EMPLOYMENT_STATUSES or status in PLANNED_STATUSES


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(",", "").replace("$", ""))
    except InvalidOperation:
        return None


def _day(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _int(value: Any) -> int | None:
    parsed = _dec(value)
    return int(parsed) if parsed is not None else None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _cash_cost(salary: Decimal | None, variable: Decimal | None, benefits_pct: Decimal | None) -> Decimal:
    return ((salary or Decimal("0")) + (variable or Decimal("0"))) * (Decimal("1") + (benefits_pct or Decimal("0")))


def employee_from_loaded_row(row: dict[str, Any]) -> RosterEmployee:
    """Map one Employees CSV row. ``commission_target`` is the sales share of ``variable_comp``, so it is not added again."""
    salary = _dec(row.get("base_salary"))
    variable = _dec(row.get("variable_comp"))
    benefits = _dec(row.get("benefits_load_pct"))
    cash_cost = _dec(row.get("fully_loaded_cash_cost"))
    return RosterEmployee(
        employee_id=_text(row.get("employee_id")),
        department=_text(row.get("department")),
        role=_text(row.get("role")),
        level=_text(row.get("level")) or None,
        region=_text(row.get("region")) or None,
        employment_status=_text(row.get("employment_status")) or "Active",
        hire_date=_day(row.get("hire_date")),
        termination_date=_day(row.get("termination_date")),
        salary_annual=salary,
        bonus_annual=variable,
        commission_annual=Decimal("0"),
        equity_sbc_annual=_dec(row.get("equity_sbc_annual")),
        benefits_load_pct=benefits,
        quota_capacity_arr=_dec(row.get("annual_quota_arr")),
        productivity_ramp_pct=None,
        months_to_full_productivity=_int(row.get("productivity_ramp_months")),
        annual_cash_cost=cash_cost if cash_cost is not None else _cash_cost(salary, variable, benefits),
    )


def employee_from_upload(row: WorkforceEmployee) -> RosterEmployee:
    salary = row.salary_annual
    bonus = row.bonus_annual
    benefits = row.benefits_load_pct
    return RosterEmployee(
        employee_id=row.employee_id,
        department=_text(row.department),
        role=_text(row.role),
        level=row.level,
        region=row.region,
        employment_status=_text(row.employment_status) or "Active",
        hire_date=row.hire_date,
        termination_date=row.termination_date,
        salary_annual=salary,
        bonus_annual=bonus,
        commission_annual=row.commission_annual,
        equity_sbc_annual=row.equity_sbc_annual,
        benefits_load_pct=benefits,
        quota_capacity_arr=row.quota_capacity_arr,
        productivity_ramp_pct=row.productivity_ramp_pct,
        months_to_full_productivity=row.months_to_full_productivity,
        annual_cash_cost=_cash_cost(salary, bonus, benefits) + (row.commission_annual or Decimal("0")),
    )


def _loaded_rows(session: Session, organization_id: uuid.UUID, version: str) -> list[dict[str, Any]]:
    table = ROSTER_TABLES.get(version)
    if not table:
        return []
    try:
        if not table_exists(session, table):
            return []
        return fetch_table_rows(session, table, organization_id)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning("loaded roster read failed for %s: %s", table, exc)
        return []


def load_roster(session: Session, organization_id: uuid.UUID, version: str) -> tuple[list[RosterEmployee], str]:
    """Roster rows and the table they came from."""
    rows = _loaded_rows(session, organization_id, version)
    if rows:
        return [employee_from_loaded_row(r) for r in rows], ROSTER_TABLES[version]
    uploads = session.scalars(
        select(WorkforceEmployee).where(
            WorkforceEmployee.organization_id == organization_id,
            WorkforceEmployee.version == version,
        )
    )
    return [employee_from_upload(r) for r in uploads], UPLOAD_ROSTER_TABLE


def roster_present(session: Session, organization_id: uuid.UUID, version: str) -> bool:
    return bool(_loaded_rows(session, organization_id, version))


def on_roster(employee: RosterEmployee, period: date) -> bool:
    """Counted in ``period`` (month start): hired by that month and not terminated before it (same rule as the engine)."""
    if not employee.counted:
        return False
    if employee.hire_date and employee.hire_date.replace(day=1) > period:
        return False
    if employee.termination_date and employee.termination_date.replace(day=1) < period:
        return False
    return True


def roster_cost_by_department(
    employees: list[RosterEmployee], periods: list[date]
) -> dict[tuple[date, str], Decimal]:
    """Monthly roster cash cost (fully loaded cash cost / 12) by period and team."""
    out: dict[tuple[date, str], Decimal] = {}
    for employee in employees:
        monthly = employee.annual_cash_cost / 12
        for period in periods:
            if on_roster(employee, period):
                key = (period, employee.department)
                out[key] = out.get(key, Decimal("0")) + monthly
    return out
