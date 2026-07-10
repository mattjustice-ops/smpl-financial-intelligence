"""Pin gold deck reference (PPTX and/or PptxGenJS script) for Option 1 adaptation.

Usage (from backend/):
  .\\.venv312\\Scripts\\python.exe scripts\\pin_gold_deck_reference.py --period 2026-06 --pptx "tmp\\mda_deck_2026-06 v3.pptx"
  .\\.venv312\\Scripts\\python.exe scripts\\pin_gold_deck_reference.py --period 2026-06 --script "tmp\\deck-archive\\2026-06\\generate_deck_2026-06.js"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.reporting.export.deck_gold import (  # noqa: E402
    gold_pptx_path,
    gold_script_path,
    pin_gold_pptx,
    pin_gold_script,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pin gold MD&A deck reference for script adaptation")
    parser.add_argument("--period", default="2026-06")
    parser.add_argument("--pptx", type=Path, help="Reference PPTX to pin (layout fingerprint)")
    parser.add_argument("--script", type=Path, help="Reference PptxGenJS script to pin")
    args = parser.parse_args()

    if not args.pptx and not args.script:
        parser.error("Provide --pptx and/or --script")

    if args.pptx:
        if not args.pptx.is_file():
            sys.exit(f"PPTX not found: {args.pptx}")
        dest = pin_gold_pptx(args.pptx.resolve(), args.period)
        print(f"Pinned gold PPTX: {dest}")

    if args.script:
        if not args.script.is_file():
            sys.exit(f"Script not found: {args.script}")
        dest = pin_gold_script(args.script.resolve(), args.period)
        print(f"Pinned gold script: {dest}")

    print(f"Gold script path: {gold_script_path(args.period)}")
    print(f"Gold PPTX path:   {gold_pptx_path(args.period)}")


if __name__ == "__main__":
    main()
