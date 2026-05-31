"""Organizations + demo CSV upload (exact headers, no column mapping)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.demo_csv.loader import (
    SEED_FILES_IN_ORDER,
    WORKFORCE_SEED_FILES,
    SeedFileResult,
    load_demo_csv,
    seed_demo_csv_folder,
    seed_workforce_demo_folder,
)
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.services.organizations import (
    create_organization,
    get_organization_or_404,
    list_organizations,
)

org_router = APIRouter(prefix="/organizations", tags=["organizations"])
demo_csv_router = APIRouter(prefix="/demo-csv", tags=["demo-csv"])

DEMO_CSV_BUILD_ID = "gl-warehouse-v3"


@demo_csv_router.get("/ping")
def demo_csv_ping() -> dict[str, str | bool]:
    """Verify demo CSV loader includes workforce profile detection."""
    from app.services.demo_csv.detector import detect_csv_kind
    from app.services.demo_csv.workforce_csv import workforce_kind_from_filename

    headers = [
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
    ]
    return {
        "status": "ok",
        "build": DEMO_CSV_BUILD_ID,
        "workforce_comp_bands_detected": detect_csv_kind(headers) == "workforce_compensation_bands",
        "compensations_bands_filename": workforce_kind_from_filename("compensations_bands.csv")
        == "workforce_compensation_bands",
    }


@org_router.get("/", response_model=list[OrganizationOut])
def list_orgs(db: Session = Depends(get_db)) -> list[OrganizationOut]:
    return list_organizations(db)


@org_router.post("/", status_code=201, response_model=OrganizationOut)
def create_org(body: OrganizationCreate, db: Session = Depends(get_db)) -> OrganizationOut:
    return create_organization(db, body)


class DemoCsvUploadResponse(BaseModel):
    csv_kind: str
    rows_upserted: int
    validation_errors: list[dict] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)


class DemoCsvSeedResponse(BaseModel):
    organization_id: uuid.UUID
    demo_data_dir: str
    files: list[dict]


def _demo_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo_data"


def _table_exists(db: Session, table_name: str) -> bool:
    return table_name in inspect(db.get_bind()).get_table_names()


def _require_tables(db: Session, tables: list[str], *, hint: str) -> None:
    missing = [t for t in tables if not _table_exists(db, t)]
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "database_schema_not_ready",
                "missing_tables": missing,
                "hint": hint,
            },
        )


@demo_csv_router.get("/schema-status")
def schema_status(db: Session = Depends(get_db)) -> dict:
    """Check whether demo seed prerequisites exist (run alembic upgrade head if missing)."""
    from sqlalchemy import inspect as sa_inspect

    names = set(sa_inspect(db.get_bind()).get_table_names())
    return {
        "customers": "customers" in names,
        "gl_actuals": "gl_actuals" in names,
        "forecast_gl_detail": "forecast_gl_detail" in names,
        "workforce_employees": "workforce_employees" in names,
        "workforce_period_summary": "workforce_period_summary" in names,
        "ready_for_full_seed": "customers" in names,
        "ready_for_gl_upload": "gl_actuals" in names and "forecast_gl_detail" in names,
        "ready_for_workforce_seed": "workforce_employees" in names and "workforce_period_summary" in names,
        "alembic_hint": "cd backend && .venv312\\Scripts\\python.exe -m alembic upgrade head",
    }


@demo_csv_router.get("/data-status")
def data_status(
    organization_id: uuid.UUID = Query(...),
    fiscal_year: int = Query(2026),
    db: Session = Depends(get_db),
) -> dict:
    """Row counts and FY revenue rollups for GL warehouse + income statement marts."""
    from sqlalchemy import text

    from app.services.financial_statements.financial_statement_service import table_exists

    get_organization_or_404(db, organization_id)
    oid = str(organization_id)
    fy_start = f"{fiscal_year:04d}-01-01"
    fy_end = f"{fiscal_year:04d}-12-31"

    def count_table(table: str) -> int | None:
        if not table_exists(db, table):
            return None
        return int(
            db.execute(
                text(f'SELECT count(*) FROM "{table}" WHERE organization_id = :oid'),
                {"oid": oid},
            ).scalar()
            or 0
        )

    out: dict = {
        "organization_id": oid,
        "fiscal_year": fiscal_year,
        "build": DEMO_CSV_BUILD_ID,
        "tables": {
            "gl_actuals": count_table("gl_actuals"),
            "forecast_gl_detail": count_table("forecast_gl_detail"),
            "actual_income_statement": count_table("actual_income_statement"),
            "forecast_income_statement": count_table("forecast_income_statement"),
            "budget_income_statement": count_table("budget_income_statement"),
        },
    }

    if table_exists(db, "gl_actuals"):
        out["gl_actuals_by_version"] = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT coalesce(version, '') AS version,
                           count(*) AS rows,
                           round(sum(amount)::numeric, 2) AS total_amount
                    FROM gl_actuals
                    WHERE organization_id = :oid
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                {"oid": oid},
            )
        ]
        out["gl_actuals_fy"] = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT to_char(period, 'YYYY-MM') AS period,
                           version,
                           count(*) AS rows,
                           round(sum(CASE WHEN lower(coalesce(statement_category, category, '')) LIKE '%revenue%'
                                     THEN amount ELSE 0 END)::numeric, 0) AS revenue,
                           round(sum(CASE WHEN amount < 0 THEN abs(amount) ELSE 0 END)::numeric, 0) AS expenses_abs
                    FROM gl_actuals
                    WHERE organization_id = :oid
                      AND period >= :fy_start AND period <= :fy_end
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                    """
                ),
                {"oid": oid, "fy_start": fy_start, "fy_end": fy_end},
            )
        ]

    if table_exists(db, "forecast_gl_detail"):
        out["forecast_gl_fy"] = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT to_char(period, 'YYYY-MM') AS period,
                           count(*) AS rows,
                           round(sum(CASE WHEN lower(coalesce(statement_category, '')) LIKE '%revenue%'
                                     THEN forecast_amount ELSE 0 END)::numeric, 0) AS revenue,
                           round(sum(CASE WHEN lower(coalesce(line_type, '')) = 'expense'
                                     THEN abs(forecast_amount) ELSE 0 END)::numeric, 0) AS expense
                    FROM forecast_gl_detail
                    WHERE organization_id = :oid
                      AND period >= :fy_start AND period <= :fy_end
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                {"oid": oid, "fy_start": fy_start, "fy_end": fy_end},
            )
        ]

    gl_rows = out["tables"].get("gl_actuals") or 0
    fc_rows = out["tables"].get("forecast_gl_detail") or 0
    out["ready_for_management_pl_gl"] = gl_rows > 0 and fc_rows > 0
    out["csv_reference_rows"] = {
        "Actual_gl_detail.csv": 894,
        "Budget_gl_detail.csv": 1660,
        "Forecast_gl_detail.csv": 238,
    }
    return out


@demo_csv_router.post("/ensure-gl-schema")
def ensure_gl_schema(db: Session = Depends(get_db)) -> dict:
    """Create gl_actuals / forecast_gl_detail if migrations were not applied."""
    from app.services.forecast_gl_detail.service import ensure_gl_warehouse_tables
    from app.services.financial_statements.financial_statement_service import table_exists as gl_table_exists

    created = ensure_gl_warehouse_tables(db)
    return {
        "build": DEMO_CSV_BUILD_ID,
        "created_tables": created,
        "gl_actuals": gl_table_exists(db, "gl_actuals"),
        "forecast_gl_detail": gl_table_exists(db, "forecast_gl_detail"),
        "alembic_hint": "cd backend && python -m alembic upgrade head",
    }


@demo_csv_router.post("/upload", response_model=DemoCsvUploadResponse)
async def upload_demo_csv(
    organization_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    get_organization_or_404(db, organization_id)
    raw = await file.read()
    try:
        res = load_demo_csv(db, organization_id, raw, filename=file.filename)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "upload_failed", "error": str(exc)},
        ) from exc
    if res.header_error:
        raise HTTPException(status_code=400, detail=res.header_error)
    if res.integrity_error:
        hint = "Run: cd backend && python -m alembic upgrade head"
        if "gl_actuals" in res.integrity_error:
            hint = (
                f"Restart the API (demo_csv build {DEMO_CSV_BUILD_ID}), POST "
                "/api/v1/demo-csv/ensure-gl-schema, or run alembic upgrade head."
            )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "database_integrity_error",
                "detail": res.integrity_error,
                "hint": hint,
                "demo_csv_build": DEMO_CSV_BUILD_ID,
            },
        )
    assert res.csv_kind is not None
    return DemoCsvUploadResponse(
        csv_kind=res.csv_kind,
        rows_upserted=res.rows_upserted,
        validation_errors=res.validation_errors,
        warnings=res.warnings,
    )


@demo_csv_router.post("/seed", response_model=DemoCsvSeedResponse)
def seed_demo_csvs(
    organization_id: uuid.UUID = Query(..., description="Target organization UUID"),
    db: Session = Depends(get_db),
):
    get_organization_or_404(db, organization_id)
    _require_tables(
        db,
        ["customers"],
        hint="Run: cd backend; .\\.venv312\\Scripts\\python.exe -m alembic upgrade head",
    )
    folder = _demo_data_dir()
    try:
        seed_results = seed_demo_csv_folder(db, organization_id, folder)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    files_payload = [_seed_row_to_dict(r) for r in seed_results]
    return DemoCsvSeedResponse(
        organization_id=organization_id,
        demo_data_dir=str(folder),
        files=files_payload,
    )


@demo_csv_router.post("/seed-workforce")
def seed_workforce_demo_csvs(
    organization_id: uuid.UUID = Query(..., description="Target organization UUID"),
    db: Session = Depends(get_db),
):
    """Load workforce demo CSVs only + recompute (no customers table required)."""
    from datetime import date

    from app.services.workforce import feeds, service

    get_organization_or_404(db, organization_id)
    _require_tables(
        db,
        ["workforce_employees", "workforce_period_summary"],
        hint="Run: cd backend; .\\.venv312\\Scripts\\python.exe -m alembic upgrade head",
    )
    folder = _demo_data_dir()
    try:
        seed_results = seed_workforce_demo_folder(db, organization_id, folder)
        plan = service.build_workforce_plan(
            db,
            organization_id,
            scenario="Forecast",
            start_period=date(2026, 1, 1),
            end_period=date(2026, 12, 31),
            persist=True,
        )
        legacy = feeds.sync_legacy_headcount_plan(
            db,
            organization_id,
            scenario="Forecast",
            start_period=date(2026, 1, 1),
            end_period=date(2026, 12, 31),
        )
        db.commit()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e

    files_payload = [_seed_row_to_dict(r) for r in seed_results]
    return {
        "organization_id": organization_id,
        "demo_data_dir": str(folder),
        "files": files_payload,
        "periods_computed": len(plan.period_summary),
        "legacy_headcount_rows_synced": legacy,
    }


def _seed_row_to_dict(r: SeedFileResult) -> dict:
    o = r.outcome
    return {
        "filename": r.filename,
        "expected_kind": r.expected_kind,
        "csv_kind": o.csv_kind,
        "rows_upserted": o.rows_upserted,
        "validation_errors": o.validation_errors,
    }


@demo_csv_router.get("/seed-order")
def seed_order():
    return {
        "full_seed_order": [{"file": f, "kind": k} for f, k in SEED_FILES_IN_ORDER],
        "workforce_seed_order": [{"file": f, "kind": k} for f, k in WORKFORCE_SEED_FILES],
    }
