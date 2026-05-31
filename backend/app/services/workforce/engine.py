"""
Derive workforce period plans from HRIS-style source datasets.

Payroll is computed as:
  (base + bonus) × productivity_ramp × (1 + benefits_load) + commission + equity_sbc
per active FTE-month, summed by department.

Open requisitions contribute planned hire FTE with the same ramp logic from planned_start_date.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
    WorkforcePeriodSummary,
)
from app.services.workforce.constants import (
    ACTIVE_EMPLOYMENT_STATUSES,
    APPROVED_REQ_STATUSES,
    DEFAULT_BENEFITS_LOAD_PCT,
    GTM_DEPARTMENTS,
    WORKFORCE_DEPARTMENTS,
)

MONEY = Decimal("0.01")
FTE = Decimal("0.0001")


def q_money(value: Any) -> Decimal:
    if value is None or value == "":
        value = Decimal("0")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def q_fte(value: Any) -> Decimal:
    if value is None or value == "":
        value = Decimal("0")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(FTE, rounding=ROUND_HALF_UP)


def month_start(value: date) -> date:
    return value.replace(day=1)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def period_range(start_period: date, end_period: date) -> list[date]:
    current = month_start(start_period)
    end = month_start(end_period)
    periods: list[date] = []
    while current <= end:
        periods.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return periods


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _status_active(status: str | None) -> bool:
    return _norm(status).lower() in ACTIVE_EMPLOYMENT_STATUSES


def _req_approved(status: str | None) -> bool:
    return _norm(status).lower() in APPROVED_REQ_STATUSES


@dataclass
class CompPackage:
    salary_annual: Decimal
    bonus_annual: Decimal
    commission_annual: Decimal
    equity_sbc_annual: Decimal
    benefits_load_pct: Decimal
    quota_capacity_arr: Decimal


@dataclass
class PeriodDeptAccumulator:
    filled_headcount: Decimal = Decimal("0")
    planned_hire_headcount: Decimal = Decimal("0")
    base_payroll_monthly: Decimal = Decimal("0")
    bonus_monthly: Decimal = Decimal("0")
    commission_monthly: Decimal = Decimal("0")
    equity_sbc_monthly: Decimal = Decimal("0")
    benefits_load_monthly: Decimal = Decimal("0")
    quota_capacity_arr: Decimal = Decimal("0")
    productive_quota_capacity_arr: Decimal = Decimal("0")

    def add_costs(
        self,
        *,
        fte: Decimal,
        productivity: Decimal,
        comp: CompPackage,
        quota_arr: Decimal,
    ) -> None:
        prod = max(Decimal("0"), min(Decimal("1"), productivity))
        base_m = q_money(comp.salary_annual / 12)
        bonus_m = q_money(comp.bonus_annual / 12)
        comm_m = q_money(comp.commission_annual / 12)
        sbc_m = q_money(comp.equity_sbc_annual / 12)
        subtotal = (base_m + bonus_m) * prod
        benefits = q_money(subtotal * comp.benefits_load_pct)
        self.base_payroll_monthly += q_money(base_m * prod * fte)
        self.bonus_monthly += q_money(bonus_m * prod * fte)
        self.commission_monthly += q_money(comm_m * fte)
        self.equity_sbc_monthly += q_money(sbc_m * fte)
        self.benefits_load_monthly += q_money(benefits * fte)
        self.quota_capacity_arr += q_money(quota_arr * fte)
        self.productive_quota_capacity_arr += q_money(quota_arr * prod * fte)

    @property
    def total_people_cost_monthly(self) -> Decimal:
        return q_money(
            self.base_payroll_monthly
            + self.bonus_monthly
            + self.commission_monthly
            + self.equity_sbc_monthly
            + self.benefits_load_monthly
        )

    @property
    def total_headcount_fte(self) -> Decimal:
        return q_fte(self.filled_headcount + self.planned_hire_headcount)


@dataclass
class WorkforceEngineResult:
    period_rows: list[dict[str, Any]] = field(default_factory=list)
    pnl_allocations: list[dict[str, Any]] = field(default_factory=list)
    gtm_capacity: list[dict[str, Any]] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)


class WorkforcePlanningEngine:
    def __init__(self, session: Session, organization_id: uuid.UUID, *, version: str) -> None:
        self.session = session
        self.organization_id = organization_id
        self.version = version
        self.employees = self._load_employees()
        self.requisitions = self._load_requisitions()
        self.ramps = self._load_ramps()
        self.bands = self._load_bands()
        self.allocation_rules = self._load_allocation_rules()

    def _load_employees(self) -> list[WorkforceEmployee]:
        return list(
            self.session.scalars(
                select(WorkforceEmployee).where(
                    WorkforceEmployee.organization_id == self.organization_id,
                    WorkforceEmployee.version == self.version,
                )
            )
        )

    def _load_requisitions(self) -> list[WorkforceOpenRequisition]:
        return list(
            self.session.scalars(
                select(WorkforceOpenRequisition).where(
                    WorkforceOpenRequisition.organization_id == self.organization_id,
                    WorkforceOpenRequisition.version == self.version,
                )
            )
        )

    def _load_ramps(self) -> dict[tuple[str, str, str], dict[int, Decimal]]:
        out: dict[tuple[str, str, str], dict[int, Decimal]] = {}
        rows = self.session.scalars(
            select(WorkforceHiringRampAssumption).where(
                WorkforceHiringRampAssumption.organization_id == self.organization_id,
                WorkforceHiringRampAssumption.version == self.version,
            )
        )
        for row in rows:
            key = (_norm(row.department), _norm(row.role), _norm(row.level) or "")
            out.setdefault(key, {})[int(row.month_offset)] = q_money(row.productivity_pct)
        return out

    def _load_bands(self) -> dict[tuple[str, str, str, str], CompPackage]:
        out: dict[tuple[str, str, str, str], CompPackage] = {}
        rows = self.session.scalars(
            select(WorkforceCompensationBand).where(
                WorkforceCompensationBand.organization_id == self.organization_id,
                WorkforceCompensationBand.version == self.version,
            )
        )
        for row in rows:
            bonus_pct = q_money(row.bonus_target_pct or 0)
            salary = q_money(row.base_salary_annual)
            key = (_norm(row.department), _norm(row.role), _norm(row.level) or "", _norm(row.region) or "")
            out[key] = CompPackage(
                salary_annual=salary,
                bonus_annual=q_money(salary * bonus_pct),
                commission_annual=q_money(row.commission_annual or 0),
                equity_sbc_annual=q_money(row.equity_sbc_annual or 0),
                benefits_load_pct=q_money(row.benefits_load_pct or DEFAULT_BENEFITS_LOAD_PCT),
                quota_capacity_arr=q_money(row.default_quota_capacity_arr or 0),
            )
        return out

    def _load_allocation_rules(self) -> list[WorkforceDepartmentAllocationRule]:
        return list(
            self.session.scalars(
                select(WorkforceDepartmentAllocationRule).where(
                    WorkforceDepartmentAllocationRule.organization_id == self.organization_id,
                    WorkforceDepartmentAllocationRule.version == self.version,
                )
            )
        )

    def _band_key(self, department: str, role: str, level: str | None, region: str | None) -> tuple[str, str, str, str]:
        return (_norm(department), _norm(role), _norm(level) or "", _norm(region) or "")

    def _resolve_comp(
        self,
        *,
        department: str,
        role: str,
        level: str | None,
        region: str | None,
        salary_override: Decimal | None = None,
        quota_override: Decimal | None = None,
        employee: WorkforceEmployee | None = None,
    ) -> tuple[CompPackage, Decimal]:
        band = self.bands.get(self._band_key(department, role, level, region))
        salary = q_money(salary_override or (employee.salary_annual if employee else None) or (band.salary_annual if band else 0))
        bonus = q_money((employee.bonus_annual if employee and employee.bonus_annual is not None else None) or (band.bonus_annual if band else 0))
        commission = q_money((employee.commission_annual if employee else None) or (band.commission_annual if band else 0))
        equity = q_money((employee.equity_sbc_annual if employee else None) or (band.equity_sbc_annual if band else 0))
        benefits = q_money(
            (employee.benefits_load_pct if employee and employee.benefits_load_pct is not None else None)
            or (band.benefits_load_pct if band else DEFAULT_BENEFITS_LOAD_PCT)
        )
        quota = q_money(
            quota_override
            or (employee.quota_capacity_arr if employee else None)
            or (band.quota_capacity_arr if band else 0)
        )
        comp = CompPackage(
            salary_annual=salary,
            bonus_annual=bonus,
            commission_annual=commission,
            equity_sbc_annual=equity,
            benefits_load_pct=benefits,
            quota_capacity_arr=quota,
        )
        return comp, quota

    def _productivity(
        self,
        *,
        department: str,
        role: str,
        level: str | None,
        hire_or_start: date | None,
        period: date,
        employee: WorkforceEmployee | None = None,
    ) -> Decimal:
        if employee and employee.productivity_ramp_pct is not None:
            return q_money(employee.productivity_ramp_pct)
        if hire_or_start is None:
            return Decimal("1")
        offset = max(0, months_between(month_start(hire_or_start), period))
        ramp_key = (_norm(department), _norm(role), _norm(level) or "")
        ramp = self.ramps.get(ramp_key, {})
        if not ramp and employee and employee.months_to_full_productivity:
            ramp = self.ramps.get(("*", "*", str(int(employee.months_to_full_productivity))), {})
        if offset in ramp:
            return ramp[offset]
        if ramp:
            max_offset = max(ramp)
            if offset >= max_offset:
                return ramp[max_offset]
            return ramp.get(offset, Decimal("1"))
        months_full = employee.months_to_full_productivity if employee else None
        if months_full and months_full > 0:
            return q_money(min(Decimal("1"), Decimal(offset + 1) / Decimal(months_full)))
        return Decimal("1")

    def _employee_active(self, employee: WorkforceEmployee, period: date) -> bool:
        if not _status_active(employee.employment_status):
            return False
        if employee.hire_date and month_start(employee.hire_date) > period:
            return False
        if employee.termination_date and month_start(employee.termination_date) < period:
            return False
        return True

    def build(self, start_period: date, end_period: date) -> WorkforceEngineResult:
        periods = period_range(start_period, end_period)
        accum: dict[tuple[date, str], PeriodDeptAccumulator] = {}
        departments = set(WORKFORCE_DEPARTMENTS)

        for employee in self.employees:
            departments.add(_norm(employee.department))
            for period in periods:
                if not self._employee_active(employee, period):
                    continue
                dept = _norm(employee.department)
                key = (period, dept)
                acc = accum.setdefault(key, PeriodDeptAccumulator())
                acc.filled_headcount += Decimal("1")
                comp, quota = self._resolve_comp(
                    department=dept,
                    role=employee.role,
                    level=employee.level,
                    region=employee.region,
                    employee=employee,
                )
                prod = self._productivity(
                    department=dept,
                    role=employee.role,
                    level=employee.level,
                    hire_or_start=employee.hire_date,
                    period=period,
                    employee=employee,
                )
                acc.add_costs(fte=Decimal("1"), productivity=prod, comp=comp, quota_arr=quota)

        for req in self.requisitions:
            if not _req_approved(req.approved_status):
                continue
            start = req.planned_start_date or req.target_hire_date
            if start is None:
                continue
            departments.add(_norm(req.department))
            for period in periods:
                if month_start(start) > period:
                    continue
                dept = _norm(req.department)
                key = (period, dept)
                acc = accum.setdefault(key, PeriodDeptAccumulator())
                acc.planned_hire_headcount += Decimal("1")
                comp, quota = self._resolve_comp(
                    department=dept,
                    role=req.role,
                    level=req.level,
                    region=req.region,
                    salary_override=req.salary_annual_override,
                    quota_override=req.quota_capacity_arr_override,
                )
                prod = self._productivity(
                    department=dept,
                    role=req.role,
                    level=req.level,
                    hire_or_start=start,
                    period=period,
                )
                acc.add_costs(fte=Decimal("1"), productivity=prod, comp=comp, quota_arr=quota)

        period_rows: list[dict[str, Any]] = []
        pnl_map: dict[tuple[date, str], Decimal] = {}
        gtm_rows: list[dict[str, Any]] = []

        for (period, dept), acc in sorted(accum.items()):
            period_rows.append(
                {
                    "period": period,
                    "department": dept,
                    "filled_headcount": q_fte(acc.filled_headcount),
                    "planned_hire_headcount": q_fte(acc.planned_hire_headcount),
                    "total_headcount_fte": acc.total_headcount_fte,
                    "base_payroll_monthly": acc.base_payroll_monthly,
                    "bonus_monthly": acc.bonus_monthly,
                    "commission_monthly": acc.commission_monthly,
                    "equity_sbc_monthly": acc.equity_sbc_monthly,
                    "benefits_load_monthly": acc.benefits_load_monthly,
                    "total_people_cost_monthly": acc.total_people_cost_monthly,
                    "quota_capacity_arr": acc.quota_capacity_arr,
                    "productive_quota_capacity_arr": acc.productive_quota_capacity_arr,
                }
            )
            if dept in GTM_DEPARTMENTS:
                reps_fte = acc.filled_headcount + acc.planned_hire_headcount if dept == "Sales" else acc.total_headcount_fte
                gtm_rows.append(
                    {
                        "period": period,
                        "department": dept,
                        "quota_carrying_reps_fte": q_fte(reps_fte),
                        "quota_capacity_arr": acc.quota_capacity_arr,
                        "productive_quota_capacity_arr": acc.productive_quota_capacity_arr,
                    }
                )
            for rule in self.allocation_rules:
                if _norm(rule.department) != dept:
                    continue
                if rule.effective_start and period < month_start(rule.effective_start):
                    continue
                if rule.effective_end and period > month_start(rule.effective_end):
                    continue
                pnl_key = (period, _norm(rule.pnl_line))
                pnl_map[pnl_key] = pnl_map.get(pnl_key, Decimal("0")) + q_money(acc.total_people_cost_monthly * rule.allocation_pct)

        validations: list[dict[str, Any]] = []
        if not self.employees and not self.requisitions:
            validations.append(
                {
                    "scenario": self.version,
                    "period": start_period,
                    "validation_name": "workforce_source_data_missing",
                    "status": "warning",
                    "message": "Upload workforce_employees and/or workforce_open_requisitions to derive payroll.",
                }
            )
        legacy_manual = self._legacy_manual_payroll_flag()
        if legacy_manual:
            validations.append(
                {
                    "scenario": self.version,
                    "period": start_period,
                    "validation_name": "legacy_manual_payroll_detected",
                    "status": "warning",
                    "message": "forecast_headcount_plan still has manual monthly_payroll_cost; derived payroll should be authoritative.",
                }
            )

        return WorkforceEngineResult(
            period_rows=period_rows,
            pnl_allocations=[{"period": p, "pnl_line": line, "amount": amt} for (p, line), amt in sorted(pnl_map.items())],
            gtm_capacity=gtm_rows,
            validations=validations,
        )

    def _legacy_manual_payroll_flag(self) -> bool:
        if self.version != "Forecast":
            return False
        from app.models.demo_finance import ForecastHeadcountPlan

        row = self.session.scalar(
            select(ForecastHeadcountPlan.monthly_payroll_cost)
            .where(
                ForecastHeadcountPlan.organization_id == self.organization_id,
                ForecastHeadcountPlan.monthly_payroll_cost.isnot(None),
                ForecastHeadcountPlan.monthly_payroll_cost != 0,
            )
            .limit(1)
        )
        return row is not None

    def persist_summary(self, result: WorkforceEngineResult) -> int:
        self.session.execute(
            delete(WorkforcePeriodSummary).where(
                WorkforcePeriodSummary.organization_id == self.organization_id,
                WorkforcePeriodSummary.version == self.version,
            )
        )
        for row in result.period_rows:
            self.session.add(
                WorkforcePeriodSummary(
                    organization_id=self.organization_id,
                    version=self.version,
                    period=row["period"],
                    department=row["department"],
                    filled_headcount=row["filled_headcount"],
                    planned_hire_headcount=row["planned_hire_headcount"],
                    total_headcount_fte=row["total_headcount_fte"],
                    base_payroll_monthly=row["base_payroll_monthly"],
                    bonus_monthly=row["bonus_monthly"],
                    commission_monthly=row["commission_monthly"],
                    equity_sbc_monthly=row["equity_sbc_monthly"],
                    benefits_load_monthly=row["benefits_load_monthly"],
                    total_people_cost_monthly=row["total_people_cost_monthly"],
                    quota_capacity_arr=row["quota_capacity_arr"],
                    productive_quota_capacity_arr=row["productive_quota_capacity_arr"],
                )
            )
        self.session.flush()
        return len(result.period_rows)
