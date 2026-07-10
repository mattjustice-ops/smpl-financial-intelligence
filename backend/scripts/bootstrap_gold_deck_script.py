"""Bootstrap a gold PptxGenJS reference script from a pinned reference PPTX.

The user provides the finished deck (.pptx). This reads that deck's structure, combines it
with live warehouse data, and asks Claude to write the generator script we adapt on future
exports. The user does not need to supply a separate script file.

Usage (from backend/):
  .\\.venv312\\Scripts\\python.exe scripts\\bootstrap_gold_deck_script.py --period 2026-06
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

from local_db_url import prepare_local_database_env

ORG_ID = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")

BOOTSTRAP_SYSTEM = """You write a complete Node.js PptxGenJS script that reproduces a reference board deck.

You receive:
1. LAYOUT BLUEPRINT — extracted from the reference .pptx (text blocks, tables, charts, positions in inches)
2. DATA PAYLOAD — JSON from the warehouse for the close period

Reproduce the reference layout faithfully: same slide count, element positions, chart types,
table column headers, KPI label formats, section titles, and footer patterns.

Use values from the DATA PAYLOAD (not hardcoded blueprint sample numbers) for all metrics.
Copy formatted money strings from the payload verbatim.

Technical:
- const pptxgen = require("pptxgenjs"); pptx.layout = "LAYOUT_WIDE"
- Use pptx.ShapeType and pptx.ChartType on the pptx instance (never pptxgen.ShapeType)
- End with pptx.writeFile({ fileName: "OUTPUT.pptx" })
- Return raw JavaScript only — no markdown fences
"""


def _load_env_from_backend() -> None:
    """Load DATABASE_URL and ANTHROPIC_API_KEY from backend/.env if not already set."""
    import os
    import re

    for name in (".env", "secrets.env", ".env.local"):
        path = BACKEND_ROOT / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)\s*$", line)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def main() -> None:
    _load_env_from_backend()
    parser = argparse.ArgumentParser(description="Bootstrap gold deck script from reference PPTX")
    parser.add_argument("--period", default="2026-06")
    parser.add_argument(
        "--pptx",
        type=Path,
        help="Reference PPTX (default: gold pinned copy or tmp/mda_deck_<period> v3.pptx)",
    )
    args = parser.parse_args()

    prepare_local_database_env()

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.services.commentary.llm_factory import build_commentary_llm_client
    from app.services.reporting.export.data_collector import collect_reporting_bundle
    from app.services.reporting.export.deck_gold import (
        extract_pptx_blueprint,
        gold_script_path,
        pin_gold_script,
        resolve_gold_pptx,
    )
    from app.services.reporting.export.prompt5_deck import (
        _generate_deck_script_text,
        _prepare_script,
        _run_node_script,
        build_prompt5_payload,
    )

    if not get_settings().anthropic_api_key:
        sys.exit("ANTHROPIC_API_KEY required")

    ref_pptx = args.pptx
    if ref_pptx is None:
        ref_pptx = resolve_gold_pptx(args.period)
        if ref_pptx is None:
            fallback = BACKEND_ROOT / "tmp" / f"mda_deck_{args.period} v3.pptx"
            ref_pptx = fallback if fallback.is_file() else gold_pptx_path(args.period)
    if not ref_pptx.is_file():
        sys.exit(f"Reference PPTX not found: {ref_pptx}")

    print(f"Reading layout blueprint from {ref_pptx}...")
    blueprint = extract_pptx_blueprint(ref_pptx.resolve())

    year = args.period[:4]
    db = SessionLocal()
    try:
        bundle = collect_reporting_bundle(
            db,
            ORG_ID,
            scenario="Combined",
            start_period=f"{year}-01",
            end_period=f"{year}-12",
            as_of_period=args.period,
            include_ai_commentary=False,
        )
        ts_data = cash_bridge_data = None
        try:
            from app.services.reporting.three_statement_payload import build_cash_bridge_data, build_ts_data

            ts_data = build_ts_data(
                db, ORG_ID, as_of=args.period, start_period=f"{year}-01", end_period=f"{year}-12"
            )
            cash_bridge_data = build_cash_bridge_data(
                db, ORG_ID, start_period=f"{year}-01", end_period=f"{year}-12"
            )
        except Exception:
            pass
        payload = build_prompt5_payload(bundle, ts_data=ts_data, cash_bridge_data=cash_bridge_data)
    finally:
        db.close()

    user_message = (
        "Write a PptxGenJS script that reproduces the reference deck layout below.\n"
        "Populate it with values from the DATA PAYLOAD.\n\n"
        f"LAYOUT BLUEPRINT (from {ref_pptx.name}):\n"
        f"{json.dumps(blueprint, separators=(',', ':'))}\n\n"
        f"DATA PAYLOAD:\n"
        f"{json.dumps(payload, separators=(',', ':'))}\n\n"
        "Return the complete Node.js script only."
    )

    print("Asking Claude to write gold reference script (one-time bootstrap)...")
    client = build_commentary_llm_client()
    script_text = _generate_deck_script_text(client, user_message, system_prompt=BOOTSTRAP_SYSTEM)

    with tempfile.TemporaryDirectory(prefix="smpl-bootstrap-") as tmp:
        tmp_dir = Path(tmp)
        out_pptx = tmp_dir / f"mda_deck_{args.period}.pptx"
        script_path = tmp_dir / "generate_deck.js"
        prepared = _prepare_script(script_text, out_pptx)
        script_path.write_text(prepared, encoding="utf-8")
        print("Validating script with Node...")
        _run_node_script(script_path, out_pptx)
        print(f"Node OK — output {out_pptx.stat().st_size:,} bytes")

        staging = BACKEND_ROOT / "tmp" / f"_bootstrap_script_{args.period}.js"
        staging.write_text(prepared, encoding="utf-8")
        dest = pin_gold_script(staging, args.period)
        staging.unlink(missing_ok=True)
        print(f"Pinned gold script: {dest}")
        print("Future exports will adapt from this script + fresh monthly data.")


if __name__ == "__main__":
    main()
