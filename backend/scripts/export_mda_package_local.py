"""Build SMPL_MDA_Package XLSX locally via Claude Prompt 2.

Usage (from backend folder, with DATABASE_URL and ANTHROPIC_API_KEY set):
  .\\.venv312\\Scripts\\python.exe scripts\\export_mda_package_local.py

Writes: %USERPROFILE%\\Downloads\\SMPL_MDA_Package_<period>.xlsx
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))
from local_db_url import prepare_local_database_env

ORG_ID = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
CLOSE_PERIOD = os.environ.get("MDA_CLOSE_PERIOD", "2026-06")


def main() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.database_url and not os.environ.get("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = settings.database_url

    host_hint = prepare_local_database_env()
    print(f"Neon host: {host_hint}")

    from app.db.session import SessionLocal
    from app.services.reporting.export.board_export_service import build_mda_package_xlsx_bytes
    from app.services.reporting.export.data_collector import collect_reporting_bundle

    skip_claude = os.environ.get("MDA_DATA_ONLY", "").strip().lower() in ("1", "true", "yes")
    if not settings.anthropic_api_key and not skip_claude:
        print("ANTHROPIC_API_KEY is required for Claude Prompt 2 MDA package generation.")
        print("Set MDA_DATA_ONLY=1 to export warehouse metrics without commentary.")
        print("Add ANTHROPIC_API_KEY to backend\\secrets.env or backend\\.env")
        sys.exit(1)
    if skip_claude:
        print("MDA_DATA_ONLY=1 — exporting metrics refresh without Claude commentary.")

    year = CLOSE_PERIOD[:4]
    month_label = {
        "01": "January",
        "02": "February",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December",
    }.get(CLOSE_PERIOD[5:7], CLOSE_PERIOD[5:7])

    print(f"Building SMPL_MDA_Package (Claude Prompt 2) for org {ORG_ID} period {CLOSE_PERIOD}...")

    db = SessionLocal()
    try:
        bundle = collect_reporting_bundle(
            db,
            ORG_ID,
            scenario="Combined",
            start_period=f"{year}-01",
            end_period=f"{year}-12",
            as_of_period=CLOSE_PERIOD,
            include_ai_commentary=False,
        )
        ts_data = None
        cash_bridge_data = None
        try:
            from app.services.reporting.three_statement_payload import build_cash_bridge_data, build_ts_data

            ts_data = build_ts_data(
                db,
                ORG_ID,
                as_of=CLOSE_PERIOD,
                start_period=f"{year}-01",
                end_period=f"{year}-12",
            )
            cash_bridge_data = build_cash_bridge_data(
                db,
                ORG_ID,
                start_period=f"{year}-01",
                end_period=f"{year}-12",
            )
        except Exception:
            pass
        content, source = build_mda_package_xlsx_bytes(
            bundle,
            ts_data=ts_data,
            cash_bridge_data=cash_bridge_data,
        )
    finally:
        db.close()

    filename = f"SMPL_MDA_Package_{month_label}{year}.xlsx"
    primary = Path.home() / "Downloads" / filename
    fallback = BACKEND_ROOT / "tmp" / filename
    try:
        primary.write_bytes(content)
        print(f"Wrote {primary} ({len(content)} bytes, source={source})")
    except PermissionError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_bytes(content)
        print(
            f"Could not overwrite {primary} (file may be open). "
            f"Wrote {fallback} ({len(content)} bytes, source={source})"
        )


if __name__ == "__main__":
    main()
