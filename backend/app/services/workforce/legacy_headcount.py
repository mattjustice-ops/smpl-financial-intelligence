"""Fallback / overlay headcount from legacy headcount_plan tables and physical warehouse uploads."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastHeadcountPlan, HeadcountPlan, WarehouseCsvRow
from app.services.workforce.engine import month_start, q_fte, q_money

logger = logging.getLogger(__name__)

PHYSICAL_HEADCOUNT_TABLES: dict[str, str] = {
    "Actual": "actual_headcount_plan",
    "Budget": "budget_headcount_plan",
    # Separate from typed ORM mart `forecast_headcount_plan` (same name collision broke uploads).
    "Forecast": "forecast_headcount_plan_upload",
}

# Typed ORM tables — do not raw SELECT * (schema differs from landing tables).
PHYSICAL_ORM_TABLE_NAMES: frozenset[str] = frozenset({"forecast_headcount_plan"})

WAREHOUSE_HEADCOUNT_KINDS: dict[str, tuple[str, ...]] = {
    "Actual": ("headcount_plan", "actual_headcount_plan"),
    "Budget": ("headcount_plan", "budget_headcount_plan"),
    "Forecast": ("forecast_headcount_plan", "forecast_headcount_plan_upload"),
}

HEADCOUNT_FIELD_ALIASES = (
    "headcount_ending",
    "headcount_end",
    "headcount_ending_fte",
    "headcount",
    "total_headcount",
    "fte",
)

HEADCOUNT_BEGINNING_ALIASES = ("headcount_beginning", "beginning_headcount", "headcount_start")
NEW_HIRES_ALIASES = ("new_hires", "planned_hires", "hires", "starts")
ATTRITION_ALIASES = ("attrition", "terminations", "turnover", "exits")
OPEN_REQ_ALIASES = ("open_requisitions", "open_reqs", "open_requisition_count")
QUOTA_ARR_ALIASES = ("quota_capacity_arr", "quota_arr")
PRODUCTIVE_QUOTA_ALIASES = ("ramped_quota_capacity_arr", "productive_quota_capacity_arr")

PERIOD_FIELD_ALIASES = ("period", "forecast_period", "month", "reporting_period")
DEPARTMENT_FIELD_ALIASES = ("department", "dept", "cost_center", "team")
COST_FIELD_ALIASES = (
    "monthly_gaap_payroll_cost",
    "monthly_cash_payroll_cost",
    "total_people_cost",
    "monthly_payroll_cost",
    "payroll_cost",
    "people_cost",
)
SBC_FIELD_ALIASES = ("monthly_sbc", "equity_sbc_monthly", "sbc")

_NUMBER_RE = __import__("re").compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")


def _coerce_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip()
        if not s or s.lower() in {"n/a", "na", "none", "null", "-"}:
            return None
        negative = s.startswith("(") and s.endswith(")")
        match = _NUMBER_RE.search(s.replace("$", "").replace("€", "").replace("£", ""))
        if match is None:
            return None
        try:
            parsed = Decimal(match.group(0).replace(",", ""))
        except InvalidOperation:
            return None
        if "%" in s:
            parsed = parsed / Decimal("100")
        return -parsed if negative else parsed
    return None


def _coerce_period(value: Any) -> date | str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().replace(day=1)
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if len(s) == 7 and s[4] == "-" and s[:4].isdigit() and s[5:].isdigit():
            return f"{s}-01"
        if len(s) == 6 and s[:4].isdigit() and s[4:].isdigit():
            return f"{s[:4]}-{s[4:]}-01"
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date().replace(day=1)
            except ValueError:
                continue
    return None


@dataclass(frozen=True)
class LegacyHeadcountSnapshot:
    period: date
    department: str
    headcount_beginning: Decimal
    new_hires: Decimal
    attrition: Decimal
    headcount_ending: Decimal
    open_requisitions: Decimal = Decimal("0")
    people_cost: Decimal = Decimal("0")
    equity_sbc_monthly: Decimal = Decimal("0")
    quota_capacity_arr: Decimal = Decimal("0")
    productive_quota_capacity_arr: Decimal = Decimal("0")

    @property
    def headcount(self) -> Decimal:
        """Period-end filled FTE (alias for headcount_ending)."""
        return self.headcount_ending


def _normalize_version(scenario: str) -> str:
    version = scenario.strip()
    if version not in {"Actual", "Budget", "Forecast"}:
        version = "Forecast" if version.lower() == "forecast" else "Actual"
    return version


def _legacy_model(version: str) -> type[HeadcountPlan] | type[ForecastHeadcountPlan]:
    return ForecastHeadcountPlan if version == "Forecast" else HeadcountPlan


def _table_exists(session: Session, table_name: str) -> bool:
    try:
        bind = session.get_bind()
        inspector = inspect(bind)
        if bind.dialect.name == "postgresql":
            return inspector.has_table(table_name, schema="public")
        return inspector.has_table(table_name)
    except Exception:
        return False


def _recover_db_session(session: Session) -> None:
    """PostgreSQL aborts the whole transaction after the first SQL error."""
    try:
        session.rollback()
    except Exception:
        pass


def _mapping_to_dict(mapping: Any) -> dict[str, Any]:
    if isinstance(mapping, dict):
        return dict(mapping)
    try:
        return dict(mapping)
    except Exception:
        return {}


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return month_start(value)
    coerced = _coerce_period(value)
    if isinstance(coerced, date):
        return month_start(coerced)
    if isinstance(coerced, str):
        try:
            return month_start(date.fromisoformat(coerced))
        except ValueError:
            return None
    return None


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = _coerce_decimal(value)
    except Exception:
        return None
    if parsed is None:
        return None
    if isinstance(parsed, Decimal):
        return parsed
    return Decimal(str(parsed))


def _first_value(row: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _parse_headcount_flow(
    row: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
    """Resolve beginning + hires - attrition = ending from uploaded headcount plan rows."""
    beginning = _as_decimal(_first_value(row, *HEADCOUNT_BEGINNING_ALIASES))
    new_hires = _as_decimal(_first_value(row, *NEW_HIRES_ALIASES)) or Decimal("0")
    attrition = _as_decimal(_first_value(row, *ATTRITION_ALIASES)) or Decimal("0")
    ending = _as_decimal(_first_value(row, *HEADCOUNT_FIELD_ALIASES))

    if ending is not None:
        ending = q_fte(ending)
        if beginning is None:
            beginning = q_fte(ending - new_hires + attrition)
        else:
            beginning = q_fte(beginning)
    elif beginning is not None:
        beginning = q_fte(beginning)
        ending = q_fte(beginning + new_hires - attrition)
    else:
        return None

    return beginning, q_fte(new_hires), q_fte(attrition), ending


def _snapshot_from_mapping(row: dict[str, Any]) -> LegacyHeadcountSnapshot | None:
    period = _as_date(_first_value(row, *PERIOD_FIELD_ALIASES))
    department = _first_value(row, *DEPARTMENT_FIELD_ALIASES)
    flow = _parse_headcount_flow(row)
    if period is None or not str(department or "").strip() or flow is None:
        return None
    beginning, new_hires, attrition, ending = flow
    people_cost = _as_decimal(_first_value(row, *COST_FIELD_ALIASES)) or Decimal("0")
    equity_sbc = _as_decimal(_first_value(row, *SBC_FIELD_ALIASES)) or Decimal("0")
    open_req = _as_decimal(_first_value(row, *OPEN_REQ_ALIASES)) or Decimal("0")
    quota = _as_decimal(_first_value(row, *QUOTA_ARR_ALIASES)) or Decimal("0")
    productive_quota = _as_decimal(_first_value(row, *PRODUCTIVE_QUOTA_ALIASES)) or Decimal("0")
    return LegacyHeadcountSnapshot(
        period=period,
        department=str(department).strip(),
        headcount_beginning=beginning,
        new_hires=new_hires,
        attrition=attrition,
        headcount_ending=ending,
        open_requisitions=q_fte(open_req),
        people_cost=q_money(people_cost),
        equity_sbc_monthly=q_money(equity_sbc),
        quota_capacity_arr=q_money(quota),
        productive_quota_capacity_arr=q_money(productive_quota),
    )


def _snapshot_from_orm(row: HeadcountPlan | ForecastHeadcountPlan) -> LegacyHeadcountSnapshot | None:
    if row.headcount is None:
        return None
    people_cost = Decimal("0")
    for candidate in (row.total_people_cost, row.monthly_payroll_cost):
        if candidate is not None and candidate != 0:
            people_cost = q_money(candidate)
            break
    ending = q_fte(row.headcount)
    return LegacyHeadcountSnapshot(
        period=month_start(row.period),
        department=(row.department or "").strip(),
        headcount_beginning=ending,
        new_hires=Decimal("0"),
        attrition=Decimal("0"),
        headcount_ending=ending,
        people_cost=people_cost,
    )


def _dedupe_snapshots(rows: list[LegacyHeadcountSnapshot]) -> list[LegacyHeadcountSnapshot]:
    by_key: dict[tuple[date, str], LegacyHeadcountSnapshot] = {}
    for row in rows:
        by_key[(row.period, row.department)] = row
    return [by_key[k] for k in sorted(by_key)]


def _load_typed_headcount_rows(
    session: Session,
    organization_id: uuid.UUID,
    *,
    version: str,
    start_period: date,
    end_period: date,
) -> list[LegacyHeadcountSnapshot]:
    model = _legacy_model(version)
    if not _table_exists(session, model.__tablename__):
        return []
    start = month_start(start_period)
    end = month_start(end_period)
    try:
        orm_rows = list(
            session.scalars(
                select(model).where(
                    model.organization_id == organization_id,
                    model.version == version,
                    model.period >= start,
                    model.period <= end,
                )
            )
        )
    except SQLAlchemyError as exc:
        _recover_db_session(session)
        logger.warning("typed headcount load failed for %s: %s", version, exc)
        return []

    out: list[LegacyHeadcountSnapshot] = []
    for row in orm_rows:
        snap = _snapshot_from_orm(row)
        if snap is not None:
            out.append(snap)
    return out


def _load_physical_headcount_rows(
    session: Session,
    organization_id: uuid.UUID,
    *,
    version: str,
    start_period: date,
    end_period: date,
) -> list[LegacyHeadcountSnapshot]:
    table_name = PHYSICAL_HEADCOUNT_TABLES.get(version)
    if not table_name or table_name in PHYSICAL_ORM_TABLE_NAMES:
        return []
    if not _table_exists(session, table_name):
        return []

    start = month_start(start_period)
    end = month_start(end_period)
    org_id = str(organization_id)
    try:
        result = session.execute(
            text(
                f'''
                SELECT * FROM "{table_name}"
                WHERE CAST(organization_id AS text) = :organization_id
                '''
            ),
            {"organization_id": org_id},
        )
    except SQLAlchemyError as exc:
        _recover_db_session(session)
        logger.warning("physical headcount load failed for %s: %s", table_name, exc)
        return []

    out: list[LegacyHeadcountSnapshot] = []
    for mapping in result.mappings():
        snap = _snapshot_from_mapping(_mapping_to_dict(mapping))
        if snap is None:
            continue
        if snap.period < start or snap.period > end:
            continue
        out.append(snap)
    return out


def _load_warehouse_headcount_rows(
    session: Session,
    organization_id: uuid.UUID,
    *,
    version: str,
    start_period: date,
    end_period: date,
) -> list[LegacyHeadcountSnapshot]:
    kinds = WAREHOUSE_HEADCOUNT_KINDS.get(version, ())
    if not kinds or not _table_exists(session, WarehouseCsvRow.__tablename__):
        return []
    start = month_start(start_period)
    end = month_start(end_period)
    try:
        warehouse_rows = list(
            session.scalars(
                select(WarehouseCsvRow).where(
                    WarehouseCsvRow.organization_id == organization_id,
                    WarehouseCsvRow.csv_kind.in_(kinds),
                )
            )
        )
    except SQLAlchemyError as exc:
        _recover_db_session(session)
        logger.warning("warehouse headcount load failed for %s: %s", version, exc)
        return []

    out: list[LegacyHeadcountSnapshot] = []
    for row in warehouse_rows:
        snap = _snapshot_from_mapping(_payload_to_dict(row.payload))
        if snap is None:
            continue
        if snap.period < start or snap.period > end:
            continue
        out.append(snap)
    return out


def load_legacy_headcount_rows(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[LegacyHeadcountSnapshot]:
    """Load headcount snapshots from typed marts, physical warehouse tables, and raw CSV payloads."""
    version = _normalize_version(scenario)
    # Physical uploads first so a missing typed mart table never blocks actual_headcount_plan.
    physical = _load_physical_headcount_rows(
        session, organization_id, version=version, start_period=start_period, end_period=end_period
    )
    warehouse = _load_warehouse_headcount_rows(
        session, organization_id, version=version, start_period=start_period, end_period=end_period
    )
    typed = _load_typed_headcount_rows(
        session, organization_id, version=version, start_period=start_period, end_period=end_period
    )
    # Physical versioned uploads win over typed demo marts; warehouse is last-resort.
    return _dedupe_snapshots([*warehouse, *typed, *physical])


def legacy_headcount_present(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
) -> bool:
    version = _normalize_version(scenario)
    if _load_physical_headcount_rows(
        session, organization_id, version=version, start_period=date(2000, 1, 1), end_period=date(2100, 12, 1)
    ):
        return True
    if _load_warehouse_headcount_rows(
        session, organization_id, version=version, start_period=date(2000, 1, 1), end_period=date(2100, 12, 1)
    ):
        return True

    model = _legacy_model(version)
    if not _table_exists(session, model.__tablename__):
        return False
    try:
        count = session.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.organization_id == organization_id,
                model.version == version,
                model.headcount.isnot(None),
                model.headcount != 0,
            )
        )
    except SQLAlchemyError:
        _recover_db_session(session)
        return False
    return bool(count and int(count) > 0)


def _legacy_people_cost(row: LegacyHeadcountSnapshot) -> Decimal:
    return q_money(row.people_cost)


def legacy_row_to_period_dict(row: LegacyHeadcountSnapshot) -> dict[str, Any]:
    filled = q_fte(row.headcount_ending)
    planned = q_fte(row.open_requisitions)
    people_cost = _legacy_people_cost(row)
    equity_sbc = q_money(row.equity_sbc_monthly)
    base_payroll = q_money(people_cost - equity_sbc) if people_cost > equity_sbc else people_cost
    return {
        "period": month_start(row.period),
        "department": row.department,
        "headcount_beginning_fte": q_fte(row.headcount_beginning),
        "new_hires_fte": q_fte(row.new_hires),
        "attrition_fte": q_fte(row.attrition),
        "headcount_ending_fte": filled,
        "filled_headcount": filled,
        "planned_hire_headcount": planned,
        "total_headcount_fte": q_fte(filled + planned),
        "base_payroll_monthly": base_payroll,
        "bonus_monthly": Decimal("0"),
        "commission_monthly": Decimal("0"),
        "equity_sbc_monthly": equity_sbc,
        "benefits_load_monthly": Decimal("0"),
        "total_people_cost_monthly": people_cost,
        "quota_capacity_arr": q_money(row.quota_capacity_arr),
        "productive_quota_capacity_arr": q_money(row.productive_quota_capacity_arr),
    }


def merge_legacy_headcount(
    period_rows: list[dict[str, Any]],
    legacy_rows: list[LegacyHeadcountSnapshot],
) -> list[dict[str, Any]]:
    """Use uploaded headcount plan rows as authoritative department detail for covered periods."""
    if not legacy_rows:
        return period_rows

    legacy_periods = {month_start(row.period) for row in legacy_rows}
    by_key: dict[tuple[date, str], dict[str, Any]] = {
        (month_start(row["period"]), row["department"]): dict(row)
        for row in period_rows
        if month_start(row["period"]) not in legacy_periods
    }

    for leg in legacy_rows:
        period = month_start(leg.period)
        dept = leg.department
        if not dept:
            continue
        by_key[(period, dept)] = legacy_row_to_period_dict(leg)

    return [by_key[k] for k in sorted(by_key)]


def mirror_snapshots_to_typed_mart(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    snapshots: list[LegacyHeadcountSnapshot],
) -> int:
    """Upsert legacy snapshots into typed headcount_plan / forecast_headcount_plan."""
    if not snapshots:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    version = _normalize_version(scenario)
    model = _legacy_model(version)
    if not _table_exists(session, model.__tablename__):
        logger.info(
            "Skipping typed headcount mirror; table %s is not present (physical upload still kept).",
            model.__tablename__,
        )
        return 0

    count = 0
    try:
        with session.begin_nested():
            for snap in snapshots:
                payload = {
                    "organization_id": organization_id,
                    "version": version,
                    "period": snap.period,
                    "department": snap.department,
                    "headcount": snap.headcount_ending,
                    "monthly_payroll_cost": snap.people_cost if snap.people_cost > 0 else None,
                    "total_people_cost": snap.people_cost if snap.people_cost > 0 else None,
                }
                stmt = pg_insert(model).values(**payload)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["organization_id", "version", "period", "department"],
                    set_={
                        "headcount": payload["headcount"],
                        "monthly_payroll_cost": payload["monthly_payroll_cost"],
                        "total_people_cost": payload["total_people_cost"],
                    },
                )
                session.execute(stmt)
                count += 1
            session.flush()
    except SQLAlchemyError as exc:
        logger.warning("typed headcount mirror failed for %s: %s", version, exc)
        return 0
    return count


def mirror_physical_headcount_upload(
    session: Session,
    organization_id: uuid.UUID,
    *,
    table_name: str,
    version_hint: str | None,
) -> int:
    version = _normalize_version(version_hint or "Actual")
    if table_name != PHYSICAL_HEADCOUNT_TABLES.get(version):
        return 0
    snapshots = _load_physical_headcount_rows(
        session,
        organization_id,
        version=version,
        start_period=date(2000, 1, 1),
        end_period=date(2100, 12, 1),
    )
    return mirror_snapshots_to_typed_mart(
        session, organization_id, scenario=version, snapshots=snapshots
    )
