"""Parse demo CSV bytes and upsert rows (PostgreSQL ON CONFLICT)."""

from __future__ import annotations

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
)
from app.models.demo_finance import (
    Customer,
    DemoCommissionPlan,
    ForecastAssumption,
    ForecastBalanceSheet,
    ForecastBookingsSummary,
    ForecastCashCollections,
    ForecastCashFlowStatement,
    ForecastGlDetail,
    ForecastHeadcountPlan,
    ForecastIncomeStatement,
    ForecastMarketingPipeline,
    ForecastMrrWaterfall,
    ForecastOpportunity,
    ForecastQuotaCapacity,
    ForecastRevenueSchedule,
    ForecastWorkingCapitalMetrics,
    GlActual,
    HeadcountPlan,
    Invoice,
    MrrWaterfall,
    Opportunity,
    Payment,
    SalesQuota,
    Subscription,
    VendorContract,
    WarehouseCsvRow,
)
from app.schemas.demo_csv import ROW_MODELS, _coerce_date, _coerce_decimal, _coerce_period
from app.services.demo_csv.detector import (
    MANAGED_COLUMNS,
    detect_csv_kind,
    header_mismatch_report,
    normalize_headers,
)

VERSION_PREFIXES: dict[str, str] = {
    "actual": "Actual",
    "actuals": "Actual",
    "budget": "Budget",
    "forecast": "Forecast",
}

PHYSICAL_VERSION_PREFIX: dict[str, str] = {
    "Actual": "actual",
    "Budget": "budget",
    "Forecast": "forecast",
}

IDENT_RE = re.compile(r"[^a-z0-9_]+")


def _norm_cell_key(key: str) -> str:
    return key.strip().lstrip("\ufeff")


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Return normalized header list and raw string rows (keys normalized)."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    headers = normalize_headers(list(reader.fieldnames))
    rows: list[dict[str, str]] = []
    for raw in reader:
        row: dict[str, str] = {}
        for k, v in raw.items():
            nk = _norm_cell_key(k or "")
            if v is None:
                row[nk] = ""
            elif isinstance(v, str):
                row[nk] = v.strip()
            else:
                row[nk] = str(v)
        rows.append(row)
    return headers, rows


def _blank_to_none(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str) and v.strip() == "":
            out[k] = None
        else:
            out[k] = v
    return out


KIND_MODEL: dict[str, type[Any]] = {
    "customers": Customer,
    "subscriptions": Subscription,
    "opportunities": Opportunity,
    "invoices": Invoice,
    "payments": Payment,
    "gl_actuals": GlActual,
    "headcount_plan": HeadcountPlan,
    "vendor_contracts": VendorContract,
    "sales_quotas": SalesQuota,
    "commission_plans": DemoCommissionPlan,
    "mrr_waterfall": MrrWaterfall,
    "forecast_assumptions": ForecastAssumption,
    "forecast_balance_sheet": ForecastBalanceSheet,
    "forecast_bookings_summary": ForecastBookingsSummary,
    "forecast_cash_collections": ForecastCashCollections,
    "forecast_cash_flow_statement": ForecastCashFlowStatement,
    "forecast_headcount_plan": ForecastHeadcountPlan,
    "forecast_income_statement": ForecastIncomeStatement,
    "forecast_marketing_pipeline": ForecastMarketingPipeline,
    "forecast_mrr_waterfall": ForecastMrrWaterfall,
    "forecast_opportunities": ForecastOpportunity,
    "forecast_quota_capacity": ForecastQuotaCapacity,
    "forecast_revenue_schedule": ForecastRevenueSchedule,
    "forecast_working_capital_metrics": ForecastWorkingCapitalMetrics,
    "forecast_gl_detail": ForecastGlDetail,
    "workforce_employees": WorkforceEmployee,
    "workforce_open_requisitions": WorkforceOpenRequisition,
    "workforce_hiring_ramp_assumptions": WorkforceHiringRampAssumption,
    "workforce_compensation_bands": WorkforceCompensationBand,
    "workforce_department_allocation_rules": WorkforceDepartmentAllocationRule,
}


RAW_WAREHOUSE_KINDS: frozenset[str] = frozenset(
    {
        "assumptions",
        "balance_sheet",
        "bookings_actual",
        "bookings_budget",
        "cash_flow_statement",
        "chart_of_accounts",
        "commission_payouts",
        "dataset_summary",
        "data_dictionary",
        "department_cost_centers",
        "department_gl_summary",
        "gl_reconciliation_summary",
        "income_statement",
        "labor_gl_detail_summary",
        "marketing_sqls_actual",
        "marketing_sqls_budget",
        "master_upload_order",
        "mrr_waterfall_actual",
        "mrr_waterfall_budget",
        "opportunity_mix_summary",
        "pipeline_marketing_reconciliation",
        "renewal_commissions",
        "renewal_pipeline",
        "revenue_recognition",
        "sales_reps",
        "upload_order",
        "vendor_payments",
        "version_split_modeling_guidance",
    }
)


def _split_versioned_filename(filename: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Return (version, base_stem) for Actual_/Budget_/Forecast_ CSV names."""
    if not filename:
        return None, None
    stem = Path(filename).name.rsplit(".", 1)[0]
    stem_lower = stem.lower().replace("-", "_")
    if "_" in stem:
        prefix, rest = stem.split("_", 1)
        version = VERSION_PREFIXES.get(prefix.lower())
        if version:
            return version, rest.lower()
    from app.services.demo_csv.workforce_csv import normalize_workforce_filename_base

    wf_base = normalize_workforce_filename_base(stem_lower)
    if wf_base:
        return None, wf_base
    if "_" not in stem:
        return None, stem_lower
    return None, stem_lower


def _safe_identifier(value: str) -> str:
    ident = IDENT_RE.sub("_", value.strip().lower()).strip("_")
    if not ident:
        raise ValueError("empty SQL identifier")
    if ident[0].isdigit():
        ident = f"_{ident}"
    return ident[:63]


def _quote_ident(value: str) -> str:
    # Identifiers are sanitized before quoting; double quotes preserve underscores.
    return f'"{_safe_identifier(value)}"'


def _physical_version_table_name(filename: Optional[str]) -> Optional[str]:
    version, base = _split_versioned_filename(filename)
    if version not in PHYSICAL_VERSION_PREFIX or not base:
        return None
    # GL detail files use typed marts (gl_actuals / forecast_gl_detail), not text landing tables.
    if base == "gl_detail":
        return None
    table = _safe_identifier(f"{PHYSICAL_VERSION_PREFIX[version]}_{base}")
    # Forecast headcount CSV lands in a text warehouse table, not the typed ORM mart.
    if table == "forecast_headcount_plan":
        return "forecast_headcount_plan_upload"
    return table


def _kind_from_filename(filename: Optional[str]) -> Optional[str]:
    from app.services.demo_csv.workforce_csv import WORKFORCE_FILENAME_BASES, workforce_kind_from_filename

    wf_kind = workforce_kind_from_filename(filename)
    if wf_kind:
        return wf_kind

    version, base = _split_versioned_filename(filename)
    if not base:
        return None

    if base in WORKFORCE_FILENAME_BASES:
        return WORKFORCE_FILENAME_BASES[base]

    if version == "Actual" and base in {
        "commission_plans",
        "customers",
        "invoices",
    }:
        return base

    if version in {"Actual", "Budget"} and base == "gl_detail":
        return "gl_actuals"

    if version == "Forecast" and base == "gl_detail":
        return "forecast_gl_detail"

    if version in {"Actual", "Budget"} and base == "headcount_plan":
        return "headcount_plan"

    if version == "Forecast":
        forecast_kind = f"forecast_{base}"
        if forecast_kind in KIND_MODEL:
            return forecast_kind

    if version is not None:
        # Preserve non-canonical versioned files independently in the raw landing table.
        return f"{version.lower()}_{base}"

    return base if base in RAW_WAREHOUSE_KINDS else None


def _version_from_filename(filename: Optional[str]) -> Optional[str]:
    version, _ = _split_versioned_filename(filename)
    return version


def _canonicalize_row(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    """Map expanded warehouse CSV column names onto canonical mart columns."""
    out = dict(row)
    if kind == "customers":
        out.setdefault("start_date", out.get("customer_start_date") or out.get("contract_start_date"))
        out.setdefault("payment_terms", out.get("billing_terms"))
    elif kind == "subscriptions":
        out.setdefault("start_date", out.get("contract_start_date"))
        out.setdefault("end_date", out.get("contract_end_date"))
    elif kind == "opportunities":
        out.setdefault("rep_id", out.get("owner_rep_id"))
    elif kind == "gl_actuals":
        out.setdefault("category", out.get("statement_category"))
    elif kind == "forecast_gl_detail":
        out.setdefault("scenario", out.get("scenario") or out.pop("version", None) or "Forecast")
        out.setdefault("department", out.get("department") or "")
        out.setdefault("sub_department", out.get("sub_department") or "")
        out.setdefault("management_view_include", out.get("management_view_include") or "Yes")
        out.setdefault("accounting_view_include", out.get("accounting_view_include") or "Yes")
        out.setdefault("sbc_flag", out.get("sbc_flag") or "No")
        out.setdefault("one_time_flag", out.get("one_time_flag") or "No")
        out.setdefault("non_cash_flag", out.get("non_cash_flag") or "No")
    elif kind == "commission_plans":
        out.setdefault("clawback_window", out.get("clawback_window_months"))
    elif kind.startswith("workforce_"):
        from app.services.demo_csv.workforce_csv import canonicalize_workforce_row

        return canonicalize_workforce_row(kind, out)
    return out


def _orm_upsert(session: Session, model: type[Any], batch: list[dict[str, Any]], *, chunk_size: int = 500) -> None:
    if not batch:
        return
    table = model.__table__
    pk_cols = [c.name for c in table.primary_key.columns]
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i : i + chunk_size]
        stmt = pg_insert(model).values(chunk)
        excluded = stmt.excluded
        upd: dict[str, Any] = {}
        for col in table.columns:
            if col.name in pk_cols or col.name == "created_at":
                continue
            upd[col.name] = getattr(excluded, col.name)
        upd["updated_at"] = func.now()
        session.execute(stmt.on_conflict_do_update(index_elements=pk_cols, set_=upd))


def _row_to_payload(kind: str, row_model: BaseModel, *, version_hint: Optional[str] = None) -> dict[str, Any]:
    data = row_model.model_dump()
    if kind == "gl_actuals":
        data["version"] = data.get("version") or version_hint or "Actual"
        data["category"] = data.get("category") or data.get("statement_category")
        data["department"] = data.get("department") or ""
        data["cost_center"] = data.get("cost_center") or ""
        data["sub_department"] = data.get("sub_department") or ""
        data["vendor_id"] = data.get("vendor_id") or ""
        data["source_file"] = data.get("source_file") or ""
        data["source_record_id"] = data.get("source_record_id") or ""
        data["subsidiary"] = data.get("subsidiary") or ""
        data["source_system"] = data.get("source_system") or "demo"
    if kind == "forecast_gl_detail":
        data["scenario"] = (
            data.get("scenario") or data.get("version") or version_hint or "Forecast"
        )
        data["department"] = data.get("department") or ""
        data["sub_department"] = data.get("sub_department") or ""
        data["management_view_include"] = data.get("management_view_include") or "Yes"
        data["accounting_view_include"] = data.get("accounting_view_include") or "Yes"
        data["sbc_flag"] = data.get("sbc_flag") or "No"
        data["one_time_flag"] = data.get("one_time_flag") or "No"
        data["non_cash_flag"] = data.get("non_cash_flag") or "No"
        data.pop("version", None)
    if kind == "headcount_plan":
        data["version"] = data.get("version") or version_hint or "Actual"
        if data.get("headcount") is None and data.get("headcount_ending") is not None:
            data["headcount"] = data["headcount_ending"]
        data.pop("headcount_ending", None)
        data.pop("headcount_beginning", None)
    if kind == "forecast_headcount_plan":
        data["version"] = data.get("version") or version_hint or "Forecast"
        if data.get("headcount") is None and data.get("headcount_ending") is not None:
            data["headcount"] = data["headcount_ending"]
        data.pop("headcount_ending", None)
        data.pop("headcount_beginning", None)
    if kind == "sales_quotas":
        data["segment"] = data.get("segment") or ""
    if kind.startswith("forecast_") and kind not in ("forecast_assumptions", "forecast_gl_detail"):
        data["version"] = data.get("version") or version_hint or "Forecast"
    if kind.startswith("workforce_"):
        data["version"] = data.get("version") or version_hint or "Forecast"
    return data


@dataclass
class LoadResult:
    csv_kind: Optional[str]
    rows_upserted: int
    validation_errors: list[dict[str, Any]] = field(default_factory=list)
    header_error: Optional[dict[str, Any]] = None
    integrity_error: Optional[str] = None
    warnings: list[dict[str, Any]] = field(default_factory=list)
    workforce_recompute: dict[str, Any] | None = None
    did_upsert: bool = False


def _json_safe_value(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def _pk_key_as_dict(pk_cols: list[str], key: tuple[Any, ...]) -> dict[str, Any]:
    return {pk_cols[i]: _json_safe_value(key[i]) for i in range(len(pk_cols))}


def _dedupe_batch_by_pk(
    model: type[Any], batch: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collapse duplicate primary keys in one upload; last row wins.

    PostgreSQL rejects a single INSERT … ON CONFLICT batch that touches the same
  row twice. Returns (deduped_rows, list of dropped duplicate keys for warnings).
    """
    pk_cols = [c.name for c in model.__table__.primary_key.columns]
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    dropped_keys: list[dict[str, Any]] = []
    for row in batch:
        key = tuple(row.get(c) for c in pk_cols)
        if key in by_key:
            dropped_keys.append(_pk_key_as_dict(pk_cols, key))
        by_key[key] = row
    return list(by_key.values()), dropped_keys


def _load_raw_warehouse_csv(
    session: Session,
    organization_id: uuid.UUID,
    *,
    csv_kind: str,
    filename: Optional[str],
    rows: list[dict[str, str]],
) -> LoadResult:
    session.execute(
        delete(WarehouseCsvRow).where(
            WarehouseCsvRow.organization_id == organization_id,
            WarehouseCsvRow.csv_kind == csv_kind,
        )
    )
    payloads = [
        {
            "organization_id": organization_id,
            "csv_kind": csv_kind,
            "source_filename": filename,
            "source_row_number": idx,
            "payload": _blank_to_none({k: v for k, v in raw.items() if k not in MANAGED_COLUMNS}),
        }
        for idx, raw in enumerate(rows, start=2)
    ]
    _orm_upsert(session, WarehouseCsvRow, payloads)
    return LoadResult(csv_kind, len(payloads), did_upsert=True)


def _sync_physical_version_table(
    session: Session,
    *,
    table_name: str,
    headers: list[str],
) -> list[str]:
    """Create/update physical actual_* / budget_* landing table columns.

    CSV columns are stored as text so newly separated files can evolve without
    requiring a code migration for every reporting artifact.
    """
    csv_columns = [
        _safe_identifier(h)
        for h in headers
        if h not in MANAGED_COLUMNS and _safe_identifier(h) not in {"source_row_number", "source_filename"}
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for col in csv_columns:
        if col not in seen:
            seen.add(col)
            deduped.append(col)

    q_table = _quote_ident(table_name)
    session.execute(
        text(
            f"""
            create table if not exists {q_table} (
                organization_id uuid not null references organizations(id) on delete cascade,
                source_row_number integer not null,
                source_filename text,
                created_at timestamptz not null default now(),
                updated_at timestamptz not null default now(),
                primary key (organization_id, source_row_number)
            )
            """
        )
    )
    session.execute(text(f"alter table {q_table} add column if not exists source_row_number integer"))
    session.execute(text(f"alter table {q_table} add column if not exists source_filename text"))
    for col in deduped:
        session.execute(text(f"alter table {q_table} add column if not exists {_quote_ident(col)} text"))
    return deduped


def _physical_column_types(session: Session, table_name: str) -> dict[str, str]:
    rows = session.execute(
        text(
            """
            select column_name, data_type
            from information_schema.columns
            where table_schema = 'public' and table_name = :table_name
            """
        ),
        {"table_name": _safe_identifier(table_name)},
    ).mappings()
    return {str(row["column_name"]): str(row["data_type"]).lower() for row in rows}


def _physical_required_columns(session: Session, table_name: str) -> set[str]:
    rows = session.execute(
        text(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public'
              and table_name = :table_name
              and is_nullable = 'NO'
              and column_default is null
            """
        ),
        {"table_name": _safe_identifier(table_name)},
    ).scalars()
    return {str(row) for row in rows}


def _coerce_physical_value(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if data_type in {"numeric", "decimal", "double precision", "real", "integer", "bigint"}:
        return _coerce_decimal(value)
    if data_type in {"date", "timestamp with time zone", "timestamp without time zone"}:
        return _coerce_period(value)
    return value


# Legacy ORM tables may require columns that versioned warehouse CSVs name differently.
PHYSICAL_REQUIRED_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "forecast_opportunities": {
        "forecast_period": ("period", "forecast_period"),
    },
}

PHYSICAL_INSERT_SKIP_COLUMNS = frozenset(
    {"organization_id", "source_row_number", "source_filename", "created_at", "updated_at"}
)


def _physical_extra_insert_columns(columns: list[str], required_columns: set[str]) -> list[str]:
    """Include NOT NULL DB columns (e.g. version) that are absent from the CSV headers."""
    extra: list[str] = []
    for col in sorted(required_columns):
        if col in columns or col in extra or col in PHYSICAL_INSERT_SKIP_COLUMNS:
            continue
        extra.append(col)
    return extra


def _first_raw_value(raw: dict[str, str], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _apply_physical_required_aliases(
    table_name: str,
    row_payload: dict[str, Any],
    raw: dict[str, str],
    *,
    column_types: dict[str, str],
    required_columns: set[str],
    version_hint: Optional[str],
) -> None:
    aliases = PHYSICAL_REQUIRED_ALIASES.get(table_name, {})
    for target, sources in aliases.items():
        target_type = column_types.get(target, "text")
        existing = row_payload.get(target)
        if existing not in (None, ""):
            if target_type == "date":
                row_payload[target] = _coerce_physical_value(existing, target_type)
            continue
        for source in sources:
            if source in row_payload and row_payload[source] not in (None, ""):
                row_payload[target] = _coerce_physical_value(row_payload[source], target_type)
                break
            raw_value = _first_raw_value(raw, source)
            if raw_value is not None:
                row_payload[target] = _coerce_physical_value(raw_value, target_type)
                break
    if "scenario_name" in required_columns and not row_payload.get("scenario_name"):
        row_payload["scenario_name"] = (
            row_payload.get("scenario_name")
            or _first_raw_value(raw, "scenario_name", "version")
            or version_hint
            or "Forecast"
        )
    if "version" in required_columns and not row_payload.get("version"):
        row_payload["version"] = _first_raw_value(raw, "version") or version_hint or "Forecast"


def _is_skippable_physical_row(row_payload: dict[str, Any], *, required_columns: set[str]) -> bool:
    """Skip blank lines, section headers, and trailing empty rows in versioned CSVs."""
    for col in ("period", "forecast_period"):
        if col in required_columns and row_payload.get(col) in (None, ""):
            return True
    if "version" in required_columns and row_payload.get("version") in (None, ""):
        return True
    return False


def _load_physical_version_csv(
    session: Session,
    organization_id: uuid.UUID,
    *,
    table_name: str,
    filename: Optional[str],
    headers: list[str],
    rows: list[dict[str, str]],
) -> int:
    columns = _sync_physical_version_table(session, table_name=table_name, headers=headers)
    column_types = _physical_column_types(session, table_name)
    required_columns = _physical_required_columns(session, table_name)
    version_hint = _version_from_filename(filename)
    extra_columns = _physical_extra_insert_columns(columns, required_columns)
    for target_col in PHYSICAL_REQUIRED_ALIASES.get(table_name, {}):
        if target_col in required_columns and target_col not in columns and target_col not in extra_columns:
            extra_columns.append(target_col)
    all_insert_columns = [*columns, *extra_columns]
    q_table = _quote_ident(table_name)
    session.execute(
        text(f"delete from {q_table} where organization_id = :organization_id"),
        {"organization_id": organization_id},
    )
    if not rows:
        return 0

    quoted_columns = [
        "organization_id",
        "source_row_number",
        "source_filename",
        *[_quote_ident(c) for c in all_insert_columns],
    ]
    value_names = [
        ":organization_id",
        ":source_row_number",
        ":source_filename",
        *[f":{c}" for c in all_insert_columns],
    ]
    insert_sql = text(
        f"""
        insert into {q_table} ({", ".join(quoted_columns)})
        values ({", ".join(value_names)})
        """
    )
    payloads: list[dict[str, Any]] = []
    for idx, raw in enumerate(rows, start=2):
        row_payload: dict[str, Any] = {
            "organization_id": organization_id,
            "source_row_number": idx,
            "source_filename": filename,
        }
        for header in headers:
            if header in MANAGED_COLUMNS:
                continue
            col = _safe_identifier(header)
            if col in columns:
                row_payload[col] = _coerce_physical_value(raw.get(header), column_types.get(col, "text"))
        _apply_physical_required_aliases(
            table_name,
            row_payload,
            raw,
            column_types=column_types,
            required_columns=required_columns,
            version_hint=version_hint,
        )
        if _is_skippable_physical_row(row_payload, required_columns=required_columns):
            continue
        payloads.append(row_payload)

    for i in range(0, len(payloads), 500):
        session.execute(insert_sql, payloads[i : i + 500])
    if table_name in {"actual_headcount_plan", "budget_headcount_plan", "forecast_headcount_plan_upload"}:
        try:
            from app.services.workforce.legacy_headcount import mirror_physical_headcount_upload

            mirror_physical_headcount_upload(
                session,
                organization_id,
                table_name=table_name,
                version_hint=version_hint,
            )
        except Exception:
            # Physical warehouse rows are authoritative; typed mart mirror is optional.
            pass
    return len(payloads)


def load_demo_csv_core(
    session: Session,
    organization_id: uuid.UUID,
    content: bytes,
    *,
    filename: Optional[str] = None,
) -> LoadResult:
    """Validate and upsert within the current transaction (no commit)."""
    headers, raw_rows = parse_csv(content)
    if not headers:
        return LoadResult(
            None,
            0,
            [],
            header_error={"message": "empty_or_missing_header_row", "received_headers": headers},
        )

    filename_kind = _kind_from_filename(filename)
    physical_table = _physical_version_table_name(filename)
    if physical_table is not None:
        try:
            loaded_rows = _load_physical_version_csv(
                session,
                organization_id,
                table_name=physical_table,
                filename=filename,
                headers=headers,
                rows=raw_rows,
            )
        except (IntegrityError, DBAPIError, SQLAlchemyError) as e:
            session.rollback()
            orig = getattr(e, "orig", None)
            return LoadResult(
                physical_table,
                0,
                [],
                integrity_error=str(orig) if orig is not None else str(e),
                did_upsert=False,
            )
        # Versioned Actual_/Budget_/Forecast_ files land only in physical warehouse tables.
        return LoadResult(physical_table, loaded_rows, did_upsert=True)

    if filename_kind is not None and filename_kind not in KIND_MODEL:
        return _load_raw_warehouse_csv(
            session,
            organization_id,
            csv_kind=filename_kind,
            filename=filename,
            rows=raw_rows,
        )

    kind = filename_kind if filename_kind in KIND_MODEL else detect_csv_kind(headers)
    if kind is None:
        raw_kind = filename_kind
        if raw_kind is not None:
            return _load_raw_warehouse_csv(
                session,
                organization_id,
                csv_kind=raw_kind,
                filename=filename,
                rows=raw_rows,
            )
        return LoadResult(
            None,
            0,
            [],
            header_error={
                "message": "headers_do_not_match_any_demo_csv",
                "received_headers": headers,
                "mismatch_by_profile": header_mismatch_report(headers),
                "workforce_upload_supported": True,
                "suggested_workforce_kind": detect_csv_kind(headers),
                "suggested_kind_from_filename": _kind_from_filename(filename),
                "demo_csv_build": "workforce-upload-v2",
                "hint": (
                    "Workforce CSVs (Compensation_Bands, Employees, Open_Requisitions, "
                    "Hiring_Ramp_Assumptions, Department_Allocation_Rules) are supported. "
                    "Restart the API if suggested_workforce_kind is null."
                ),
            },
        )

    row_model_cls = ROW_MODELS[kind]
    model = KIND_MODEL[kind]
    version_hint = _version_from_filename(filename)

    from app.services.demo_csv.workforce_csv import preprocess_workforce_upload

    blank_rows = [_blank_to_none({k: v for k, v in raw.items() if k not in MANAGED_COLUMNS}) for raw in raw_rows]
    if kind.startswith("workforce_"):
        blank_rows = preprocess_workforce_upload(kind, headers, blank_rows, version_hint=version_hint)

    payloads: list[dict[str, Any]] = []
    val_errors: list[dict[str, Any]] = []
    for idx, raw in enumerate(blank_rows, start=2):
        clean = _canonicalize_row(kind, raw) if not kind.startswith("workforce_") else raw
        try:
            validated = row_model_cls.model_validate(clean)
        except ValidationError as e:
            val_errors.append({"row_index": idx, "errors": e.errors()})
            continue
        payload = _row_to_payload(kind, validated, version_hint=version_hint)
        payload["organization_id"] = organization_id
        payloads.append(payload)

    if not payloads:
        return LoadResult(kind, 0, val_errors, did_upsert=False)

    warnings: list[dict[str, Any]] = []
    workforce_recompute: dict[str, Any] | None = None
    payloads, dropped = _dedupe_batch_by_pk(model, payloads)
    if dropped:
        # Unique list of keys that appeared more than once
        seen: set[tuple[str, ...]] = set()
        unique_dropped: list[dict[str, Any]] = []
        for item in dropped:
            t = tuple(sorted(item.items()))
            if t not in seen:
                seen.add(t)
                unique_dropped.append(item)
        warnings.append(
            {
                "message": "duplicate_primary_keys_resolved",
                "primary_key_columns": [c.name for c in model.__table__.primary_key.columns],
                "duplicate_keys": unique_dropped[:25],
                "rows_dropped": len(dropped),
                "hint": (
                    "Multiple rows shared the same primary key (e.g. invoice_id). "
                    "The last row in the file was kept. Fix IDs in your CSV if that is wrong."
                ),
            }
        )

    try:
        if kind in ("gl_actuals", "forecast_gl_detail"):
            from app.services.forecast_gl_detail.service import ensure_gl_warehouse_tables

            created_tables = ensure_gl_warehouse_tables(session)
            if created_tables:
                warnings.append(
                    {
                        "message": "gl_warehouse_tables_created",
                        "tables": created_tables,
                        "hint": (
                            "GL mart tables were missing and were created automatically. "
                            "For a full schema, run: cd backend && python -m alembic upgrade head"
                        ),
                    }
                )

        _orm_upsert(session, model, payloads)
        if kind == "forecast_gl_detail":
            from app.services.financial_statements.financial_statement_service import table_exists as gl_table_exists
            from app.services.forecast_gl_detail.service import sync_forecast_gl_detail_to_gl_actuals

            synced = sync_forecast_gl_detail_to_gl_actuals(session, organization_id, payloads)
            if synced:
                warnings.append(
                    {
                        "message": "forecast_gl_synced_to_gl_actuals",
                        "rows_synced": synced,
                    }
                )
            elif not gl_table_exists(session, "gl_actuals"):
                warnings.append(
                    {
                        "message": "forecast_gl_saved_without_gl_actuals_sync",
                        "hint": (
                            "Rows were saved to forecast_gl_detail. gl_actuals sync was skipped "
                            "because the table could not be created — run alembic upgrade head."
                        ),
                    }
                )
        if kind.startswith("workforce_"):
            from app.services.workforce.integration import auto_recompute_after_upload

            workforce_recompute = auto_recompute_after_upload(session, organization_id, kind)
            if workforce_recompute:
                warnings.append(
                    {
                        "message": "workforce_auto_recompute",
                        **workforce_recompute,
                    }
                )
    except (IntegrityError, DBAPIError, SQLAlchemyError) as e:
        session.rollback()
        orig = getattr(e, "orig", None)
        return LoadResult(
            kind,
            0,
            val_errors,
            integrity_error=str(orig) if orig is not None else str(e),
            warnings=warnings,
            did_upsert=False,
        )

    return LoadResult(
        kind,
        len(payloads),
        val_errors,
        warnings=warnings,
        workforce_recompute=workforce_recompute,
        did_upsert=True,
    )


def load_demo_csv(
    session: Session,
    organization_id: uuid.UUID,
    content: bytes,
    *,
    filename: Optional[str] = None,
) -> LoadResult:
    res = load_demo_csv_core(session, organization_id, content, filename=filename)
    if res.did_upsert:
        session.commit()
    return res


# Files relative to backend/demo_data/ — order matches README (FK-safe).
SEED_FILES_IN_ORDER: list[tuple[str, str]] = [
    ("customers.csv", "customers"),
    ("subscriptions.csv", "subscriptions"),
    ("opportunities.csv", "opportunities"),
    ("invoices.csv", "invoices"),
    ("payments.csv", "payments"),
    ("gl_actuals.csv", "gl_actuals"),
    ("headcount_plan.csv", "headcount_plan"),
    ("workforce_compensation_bands.csv", "workforce_compensation_bands"),
    ("workforce_hiring_ramp_assumptions.csv", "workforce_hiring_ramp_assumptions"),
    ("workforce_department_allocation_rules.csv", "workforce_department_allocation_rules"),
    ("workforce_employees.csv", "workforce_employees"),
    ("workforce_open_requisitions.csv", "workforce_open_requisitions"),
    ("vendor_contracts.csv", "vendor_contracts"),
    ("sales_quotas.csv", "sales_quotas"),
    ("commission_plans.csv", "commission_plans"),
    ("mrr_waterfall.csv", "mrr_waterfall"),
]

WORKFORCE_SEED_FILES: list[tuple[str, str]] = [
    ("workforce_compensation_bands.csv", "workforce_compensation_bands"),
    ("workforce_hiring_ramp_assumptions.csv", "workforce_hiring_ramp_assumptions"),
    ("workforce_department_allocation_rules.csv", "workforce_department_allocation_rules"),
    ("workforce_employees.csv", "workforce_employees"),
    ("workforce_open_requisitions.csv", "workforce_open_requisitions"),
]


@dataclass
class SeedFileResult:
    filename: str
    expected_kind: str
    outcome: LoadResult


def seed_demo_csv_folder(session: Session, organization_id: uuid.UUID, folder: Path) -> list[SeedFileResult]:
    """Load every demo CSV in FK order inside a single DB transaction."""
    results: list[SeedFileResult] = []
    try:
        for fname, expected in SEED_FILES_IN_ORDER:
            path = folder / fname
            if not path.is_file():
                raise FileNotFoundError(f"Missing seed file: {path}")
            content = path.read_bytes()
            _assert_seed_profile(parse_csv(content)[0], fname, expected)
            res = load_demo_csv_core(session, organization_id, content, filename=fname)
            if res.header_error or res.integrity_error:
                msg = res.header_error or {"integrity": res.integrity_error}
                raise ValueError(f"{fname}: load failed: {msg}")
            results.append(SeedFileResult(fname, expected, res))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return results


def _assert_seed_profile(headers: list[str], filename: str, expected: str) -> None:
    from app.services.demo_csv.workforce_csv import workforce_kind_from_filename

    detected = detect_csv_kind(headers) or workforce_kind_from_filename(filename)
    if detected != expected:
        raise ValueError(
            f"{filename}: expected demo profile {expected!r}, detected {detected!r}. "
            f"Headers: {headers}"
        )


def seed_workforce_demo_folder(session: Session, organization_id: uuid.UUID, folder: Path) -> list[SeedFileResult]:
    """Load workforce demo CSVs only (no customers/opportunities)."""
    results: list[SeedFileResult] = []
    try:
        for fname, expected in WORKFORCE_SEED_FILES:
            path = folder / fname
            if not path.is_file():
                raise FileNotFoundError(f"Missing seed file: {path}")
            content = path.read_bytes()
            _assert_seed_profile(parse_csv(content)[0], fname, expected)
            res = load_demo_csv_core(session, organization_id, content, filename=fname)
            if res.header_error or res.integrity_error:
                msg = res.header_error or {"integrity": res.integrity_error}
                raise ValueError(f"{fname}: load failed: {msg}")
            results.append(SeedFileResult(fname, expected, res))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return results
