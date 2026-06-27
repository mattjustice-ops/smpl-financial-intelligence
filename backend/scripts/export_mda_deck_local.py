"""Build MD&A deck PPTX locally (bypasses Railway HTTP timeout).

Usage (from backend folder, with DATABASE_URL set):
  .\\.venv312\\Scripts\\python.exe scripts\\export_mda_deck_local.py

Writes: %USERPROFILE%\\Downloads\\mda_deck_<period>.pptx
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
USE_AI = os.environ.get("MDA_USE_AI", "true").lower() in ("1", "true", "yes")


def main() -> None:
    if not os.environ.get("DATABASE_URL", "").strip():
        raise SystemExit(
            "DATABASE_URL is not set.\n"
            "Set it to your Neon production URL, then re-run this script."
        )

    prepare_local_database_env()

    from app.db.session import SessionLocal
    from app.services.reporting.export.board_export_service import build_mda_deck_pptx_bytes
    from app.services.reporting.export.data_collector import collect_reporting_bundle

    year = CLOSE_PERIOD[:4]
    print(f"Building MDA deck for org {ORG_ID} period {CLOSE_PERIOD} (ai={USE_AI})...")

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
        content, source = build_mda_deck_pptx_bytes(
            bundle,
            use_ai_commentary=USE_AI,
            package_mode="full_board",
        )
    finally:
        db.close()

    out = Path.home() / "Downloads" / f"mda_deck_{CLOSE_PERIOD}.pptx"
    out.write_bytes(content)
    print(f"Wrote {out} ({len(content)} bytes, source={source})")


if __name__ == "__main__":
    main()
