import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.board_package_routes import board_package_router
from app.api.dashboard_routes import dashboard_router
from app.api.financial_statements_routes import financial_statements_router
from app.api.forecast_routes import forecast_router
from app.api.bookings_routes import bookings_router
from app.api.commentary_routes import commentary_router
from app.api.demo_csv_routes import demo_csv_router, org_router
from app.api.kpis_routes import kpis_router
from app.api.marketing_routes import marketing_router
from app.api.mrr_routes import mrr_router
from app.api.opportunity_routes import opportunity_router
from app.api.export_routes import export_router
from app.api.waterfall_routes import waterfall_router
from app.api.workforce_routes import workforce_router
from app.core.config import get_settings
from app.db.session import get_db
from app.services.organizations import get_organization_or_404

settings = get_settings()

# Bump when Management P&L / workforce routes change — visible in /health
SFI_BUILD_ID = "management-pl-v11-spec-table-periods"
WORKFORCE_BUILD_ID = "workforce-legacy-headcount-v6"
DEMO_CSV_BUILD_ID = "gl-warehouse-v3"
_MAIN_FILE = Path(__file__).resolve()

app = FastAPI(
    title="SaaS Financial Intelligence API",
    version="0.1.0",
    description="Local development API for the financial intelligence MVP.",
)


# Registered BEFORE export_router so this wins over any stale /export/ping on the router.
@app.get("/api/v1/export/ping")
def export_ping_main(response: Response) -> dict[str, str | bool]:
    from app.core.openai_status import openai_ping_payload

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-SFI-Api-Build"] = "openai-ping-v3"
    return openai_ping_payload()


@app.get("/api/v1/sfi/whoami")
def sfi_whoami() -> dict[str, str | bool | int | list[str]]:
    """Which main.py + Python this process loaded (debug stale uvicorn)."""
    import sys

    paths = sorted({getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")})
    return {
        "build": SFI_BUILD_ID,
        "workforce_build": WORKFORCE_BUILD_ID,
        "main_file": str(_MAIN_FILE),
        "python_executable": sys.executable,
        "cwd": str(__import__("os").getcwd()),
        "workforce_mounted": _workforce_mounted(),
        "workforce_paths": [p for p in paths if "/workforce/" in p],
        "path_count": len(paths),
    }


@app.get("/api/v1/export/whoami")
def export_whoami() -> dict[str, str | bool]:
    """Diagnostics: which Python + export_routes file this process loaded."""
    import inspect
    import sys

    import app.api.export_routes as export_routes_mod

    path = inspect.getfile(export_routes_mod)
    source = open(path, encoding="utf-8").read()
    return {
        "python_executable": sys.executable,
        "export_routes_file": path,
        "export_routes_has_api_build": "api_build" in source,
        "cwd": str(__import__("os").getcwd()),
    }


app.include_router(org_router, prefix="/api/v1")
app.include_router(demo_csv_router, prefix="/api/v1")
app.include_router(mrr_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(kpis_router, prefix="/api/v1")
app.include_router(commentary_router, prefix="/api/v1")
app.include_router(board_package_router, prefix="/api/v1")
app.include_router(financial_statements_router, prefix="/api/v1")
app.include_router(forecast_router, prefix="/api/v1")
app.include_router(marketing_router, prefix="/api/v1")
app.include_router(workforce_router, prefix="/api/v1")


@app.get("/api/v1/workforce/ping", tags=["workforce"])
def workforce_ping_inline(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Always defined in main.py - verify workforce routes and tables."""
    from sqlalchemy import text

    from app.services.dashboard.query_utils import table_exists

    required = [
        "workforce_employees",
        "workforce_open_requisitions",
        "workforce_hiring_ramp_assumptions",
        "workforce_compensation_bands",
        "workforce_department_allocation_rules",
        "workforce_period_summary",
    ]
    missing = [t for t in required if not table_exists(db, t)]
    summary_rows = 0
    if not missing:
        summary_rows = int(db.execute(text("select count(*) from workforce_period_summary")).scalar_one())
    return {
        "status": "ok" if not missing else "degraded",
        "build": WORKFORCE_BUILD_ID,
        "main_file": str(_MAIN_FILE),
        "tables_ok": len(missing) == 0,
        "missing_tables": ",".join(missing),
        "workforce_period_summary_rows": int(summary_rows),
        "routes": [
            "/api/v1/workforce/plan",
            "/api/v1/workforce/plan-debug",
            "/api/v1/workforce/recompute",
            "/api/v1/workforce/validation",
            "/api/v1/workforce/feeds/payroll",
            "/api/v1/workforce/feeds/cash-payroll",
            "/api/v1/workforce/feeds/gtm-capacity",
        ],
    }


@app.get("/api/v1/workforce/plan-debug", tags=["workforce"])
def workforce_plan_debug(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Actual"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    persist: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Build workforce plan and return diagnostics instead of response_model validation."""
    import traceback

    from pydantic import ValidationError

    from app.services.workforce import service
    from app.services.workforce.legacy_headcount import load_legacy_headcount_rows
    from app.services.workforce.schemas import WorkforcePlanResponse

    get_organization_or_404(db, organization_id)
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")

    legacy_count = 0
    try:
        legacy_count = len(
            load_legacy_headcount_rows(
                db,
                organization_id,
                scenario=scenario,
                start_period=start_period,
                end_period=end_period,
            )
        )
    except Exception as exc:
        return {
            "build": WORKFORCE_BUILD_ID,
            "status": "legacy_load_failed",
            "legacy_rows": 0,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    try:
        plan = service.build_workforce_plan(
            db,
            organization_id,
            scenario=scenario,
            start_period=start_period,
            end_period=end_period,
            persist=persist,
        )
    except Exception as exc:
        return {
            "build": WORKFORCE_BUILD_ID,
            "status": "build_failed",
            "legacy_rows": legacy_count,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    response_errors: list[Any] = []
    try:
        WorkforcePlanResponse.model_validate(plan.model_dump(mode="json"))
    except ValidationError as exc:
        response_errors = exc.errors()

    return {
        "build": WORKFORCE_BUILD_ID,
        "status": "ok" if not response_errors else "response_validation_failed",
        "legacy_rows": legacy_count,
        "period_summary_rows": len(plan.period_summary),
        "operating_metrics_rows": len(plan.operating_metrics),
        "validations": len(plan.validations),
        "filled_headcount_fte": str(
            next((m.filled_headcount_fte for m in plan.operating_metrics), 0)
        ),
        "total_headcount_fte": str(
            next((m.total_headcount_fte for m in plan.operating_metrics), 0)
        ),
        "response_errors": response_errors,
    }


@app.get("/api/v1/workforce/validation", tags=["workforce"])
def workforce_validation_inline(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
):
    from app.services.workforce import validation_service as workforce_validation_service

    get_organization_or_404(db, organization_id)
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")
    return workforce_validation_service.run_workforce_validations(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )


@app.get("/api/v1/management-pl/ping", tags=["management-pl"])
def management_pl_ping_inline() -> dict[str, str]:
    """Always defined in main.py — use to verify the correct API process is running."""
    return {
        "status": "ok",
        "build": SFI_BUILD_ID,
        "main_file": str(_MAIN_FILE),
    }


@app.get("/api/v1/management-pl/dashboard", tags=["management-pl"])
def management_pl_dashboard_inline(
    organization_id: uuid.UUID = Query(...),
    start_period: date = Query(...),
    end_period: date = Query(...),
    as_of_period: date | None = Query(None),
    period_mode: str = Query("fy"),
    view_mode: str = Query("management"),
    department: str = Query("Total Company"),
    db: Session = Depends(get_db),
):
    from app.services.management_pl.service import build_management_pl_dashboard

    get_organization_or_404(db, organization_id)
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")
    if period_mode not in ("month", "qtd", "ytd", "fy"):
        raise HTTPException(status_code=400, detail="period_mode must be month, qtd, ytd, or fy")
    try:
        return build_management_pl_dashboard(
            db,
            organization_id,
            start_period=start_period,
            end_period=end_period,
            as_of_period=as_of_period,
            period_mode=period_mode,
            view_mode=view_mode,
            department=department,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(waterfall_router, prefix="/api/v1")
app.include_router(opportunity_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Board-Package-Engine", "X-Export-Validation"],
)


@app.exception_handler(ResponseValidationError)
async def workforce_response_validation_handler(
    request: Request, exc: ResponseValidationError
) -> JSONResponse:
    """FastAPI has no default handler — without this, clients only see Internal Server Error."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "response_validation_failed",
                "path": str(request.url.path),
                "errors": exc.errors(),
            }
        },
    )


@app.on_event("startup")
def _log_board_engine() -> None:
    try:
        from app.core.config import clear_settings_cache, get_settings

        clear_settings_cache()
        s = get_settings()
        openai = "yes" if s.openai_api_key else "no"
        print(f"[SFI] OpenAI configured: {openai}")
    except Exception as exc:
        print(f"[SFI] OpenAI settings check failed: {exc}")
    try:
        from app.services.board_package.pptx_builder import PRESENTATION_ENGINE_VERSION

        print(f"[SFI] Board presentation engine: {PRESENTATION_ENGINE_VERSION}")
        print("[SFI] Export ping build: openai-ping-v3")
    except Exception as exc:
        print(f"[SFI] Board engine import failed: {exc}")
    if _management_pl_mounted():
        print("[SFI] Management P&L API: /api/v1/management-pl/dashboard")
    else:
        print("[SFI] WARN: Management P&L routes missing — restart backend (.\\start-api.ps1)")
    if _workforce_mounted():
        print(f"[SFI] Workforce API: /api/v1/workforce/ping (build={WORKFORCE_BUILD_ID})")
    else:
        print("[SFI] WARN: Workforce routes missing — restart backend (.\\start-api.ps1)")
    try:
        from app.db.session import SessionLocal
        from app.services.forecast_gl_detail.service import ensure_gl_warehouse_tables

        db = SessionLocal()
        try:
            created = ensure_gl_warehouse_tables(db)
            if created:
                print(f"[SFI] Created GL warehouse tables: {', '.join(created)}")
        finally:
            db.close()
    except Exception as exc:
        print(f"[SFI] GL warehouse table ensure failed: {exc}")
    print(f"[SFI] Demo CSV loader build: {DEMO_CSV_BUILD_ID}")


def _workforce_mounted() -> bool:
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        if "/workforce/" in path:
            return True
    return False


def _management_pl_mounted() -> bool:
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        if "management-pl" in path or "management_pl" in path:
            return True
    return False


@app.get("/api/v1/_diagnostics/routes")
def diagnostics_routes() -> dict[str, list[str]]:
    """List registered paths (debug stale uvicorn / wrong working directory)."""
    paths = sorted(
        {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")}
    )
    mpl = [p for p in paths if "management" in p]
    wf = [p for p in paths if "/workforce/" in p]
    return {"management_pl_paths": mpl, "workforce_paths": wf, "path_count": len(paths)}


@app.get("/health")
def health(response: Response) -> dict[str, str | bool]:
    """Liveness check: does not touch the database."""
    response.headers["X-SFI-Build"] = SFI_BUILD_ID
    response.headers["X-SFI-Workforce-Build"] = WORKFORCE_BUILD_ID
    return {
        "status": "ok",
        "build": SFI_BUILD_ID,
        "workforce_build": WORKFORCE_BUILD_ID,
        "demo_csv_build": DEMO_CSV_BUILD_ID,
        "management_pl": _management_pl_mounted(),
        "workforce": _workforce_mounted(),
    }


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verifies the app can open a connection and run a simple query."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/health/deps")
def health_deps() -> dict[str, str]:
    """Reports whether optional export dependencies are importable in this process."""
    import sys

    out: dict[str, str] = {"python": sys.executable}
    try:
        import xlsxwriter

        out["xlsxwriter"] = getattr(xlsxwriter, "__version__", "installed")
    except ImportError:
        out["xlsxwriter"] = "MISSING — run: pip install xlsxwriter==3.2.9 in this venv"
    try:
        import pptx  # noqa: F401

        out["python_pptx"] = "installed"
    except ImportError:
        out["python_pptx"] = "MISSING — run: pip install python-pptx"
    return out


@app.get("/")
def root() -> dict[str, str | bool]:
    return {
        "message": "SFI API — see /docs for interactive API documentation.",
        "management_pl": _management_pl_mounted(),
        "workforce": _workforce_mounted(),
    }
