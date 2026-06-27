"""Local MD&A pipeline smoke (read-only Neon — no schema changes).

Usage:
  set DATABASE_URL=postgresql://...   (same URL Railway uses — read only)
  .\\.venv312\\Scripts\\python.exe scripts\\local_mda_smoke.py
  .\\.venv312\\Scripts\\python.exe scripts\\local_mda_smoke.py --render
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))
from local_db_url import prepare_local_database_env

ORG_ID = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local MDA deck smoke (read-only DB)")
    parser.add_argument("--period", default=os.environ.get("MDA_CLOSE_PERIOD", "2026-06"))
    parser.add_argument("--render", action="store_true", help="Also render PPTX bytes")
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    host_hint = prepare_local_database_env()
    print(f"Neon host: {host_hint}")

    from app.db.session import SessionLocal
    from app.services.reporting.export.board_export_service import (
        build_mda_deck_pptx_bytes,
        build_mda_deck_smoke_result,
    )
    from app.services.reporting.export.data_collector import collect_reporting_bundle

    year = args.period[:4]
    use_ai = not args.no_ai and os.environ.get("MDA_USE_AI", "true").lower() in ("1", "true", "yes")

    print(f"Local MDA smoke | org={ORG_ID} | period={args.period} | ai={use_ai}")
    print("Read-only: queries Neon only, no SQL migrations or writes.")

    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        print("[1/3] Collecting reporting bundle from Neon...")
        bundle = collect_reporting_bundle(
            db,
            ORG_ID,
            scenario="Combined",
            start_period=f"{year}-01",
            end_period=f"{year}-12",
            as_of_period=args.period,
            include_ai_commentary=False,
        )
        t1 = time.perf_counter()
        print(f"      validation={bundle.validation.status} ({t1 - t0:.1f}s)")

        print("[2/3] Assembling slide package...")
        assembled = build_mda_deck_smoke_result(bundle, full_render=False, package_mode="full_board")
        t2 = time.perf_counter()
        print(f"      slide_count={assembled.get('slide_count')} ({t2 - t1:.1f}s)")

        if args.render:
            print("[3/3] Rendering PPTX...")
            content, source = build_mda_deck_pptx_bytes(
                bundle,
                use_ai_commentary=use_ai,
                package_mode="full_board",
            )
            t3 = time.perf_counter()
            out = Path.home() / "Downloads" / f"mda_deck_{args.period}.pptx"
            out.write_bytes(content)
            print(f"      wrote {out} ({len(content)} bytes, source={source}, {t3 - t2:.1f}s)")
        else:
            print("[3/3] Skipped PPTX render (pass --render to write Downloads file)")
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
