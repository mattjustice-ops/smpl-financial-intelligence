"""Build MD&A deck PPTX locally via Claude Prompt 5 (full fresh build from data).

Usage (from backend folder, with DATABASE_URL and ANTHROPIC_API_KEY set):
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


def main() -> None:
    host_hint = prepare_local_database_env()
    print(f"Neon host: {host_hint}")

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.services.reporting.export.board_export_service import build_mda_deck_pptx_bytes
    from app.services.reporting.export.data_collector import collect_reporting_bundle

    settings = get_settings()
    have_key = bool(settings.anthropic_api_key)
    if not have_key:
        print("ANTHROPIC_API_KEY is not set. Tie check will still run. The deck file will not be written.")

    year = CLOSE_PERIOD[:4]
    print(f"Building MD&A deck (Claude Prompt 5) for org {ORG_ID} period {CLOSE_PERIOD}...")

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
        from app.services.reporting.export.prompt5_deck import build_prompt5_payload

        payload = build_prompt5_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
        print("FACT TIES")
        for tie in payload.get("fact_ties") or []:
            mark = "OK" if tie.get("ok") else "FAIL"
            print(f"  {mark}  {tie.get('id')}: {tie.get('detail')}")
        failed = [tie for tie in (payload.get("fact_ties") or []) if not tie.get("ok")]
        print(f"Failed ties: {len(failed)}")
        watch = {
            "revenue.cm",
            "gross_margin.cm",
            "gross_margin.ytd",
            "gross_margin.fy",
            "arr.ending",
            "arr.gross_retention",
            "arr.net_retention",
            "pipeline.created",
            "pipeline.coverage",
            "arr.required_monthly_growth",
            "cash.ending",
        }
        print("WATCHED FACTS")
        seen = set()
        for fact in payload.get("facts") or []:
            if fact.get("id") not in watch:
                continue
            seen.add(fact["id"])
            print(
                f"  {fact['id']}: {fact.get('display')} status={fact.get('status')} "
                f"percent_offered={fact.get('percent_offered')}"
            )
        for missing in sorted(watch - seen):
            print(f"  {missing}: not in the registry for this close")
        content = None
        source = None
        if have_key:
            content, source = build_mda_deck_pptx_bytes(
                bundle,
                package_mode="full_board",
                ts_data=ts_data,
                cash_bridge_data=cash_bridge_data,
            )
    finally:
        db.close()

    if not content:
        print("Deck file was not written.")
        return

    primary = Path.home() / "Downloads" / f"mda_deck_{CLOSE_PERIOD}.pptx"
    fallback = BACKEND_ROOT / "tmp" / f"mda_deck_{CLOSE_PERIOD}.pptx"
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
