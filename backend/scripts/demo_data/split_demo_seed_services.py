"""Split the Board demo seed's services revenue into implementation and recurring services.

Implementation & Onboarding is non-recurring and comes from the implementation schedules
(<v>_implementation_schedule.csv, one fee per new customer by segment). Whatever services
revenue remains is recurring services revenue (support, TAMs). Total revenue, subscription
revenue and svc_rev (total services) do not change.

Writes TS_DATA in frontend/public/board/index.html (and the canonical mirror) with two new
fields per income statement row: impl_rev and rec_svc_rev. Then run
``node frontend/scripts/extract-demo-seed.mjs`` to refresh shared/smpl-demo-seed.js.

Usage:
  python split_demo_seed_services.py <implementation_data_folder>
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BOARD_FILES = (
    os.path.join(ROOT, "frontend", "public", "board", "index.html"),
    os.path.join(ROOT, "frontend", "canonical", "board", "index.html"),
)
VERSIONS = ("Actual", "Forecast", "Budget")


def implementation_by_month(folder: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for version in VERSIONS:
        totals: dict[str, float] = defaultdict(float)
        with open(os.path.join(folder, f"{version}_implementation_schedule.csv"), newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                totals[row["period"][:7]] += float(row["implementation_fee"] or 0)
        out[version] = dict(totals)
    return out


def _object_span(text: str, name: str) -> tuple[int, int]:
    match = re.search(rf"\b(?:var|const|let)\s+{name}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"{name} declaration not found")
    brace = match.end() - 1
    depth, in_str = 0, False
    for i in range(brace, len(text)):
        c = text[i]
        if in_str:
            if c == '"' and text[i - 1] != "\\":
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return brace, i + 1
    raise ValueError(f"{name} object is not closed")


def split_ts_data(ts: dict, impl: dict[str, dict[str, float]]) -> list[str]:
    log: list[str] = []
    for version in VERSIONS:
        rows = (ts.get(version) or {}).get("is") or {}
        for period, row in sorted(rows.items()):
            if row.get("svc_rev") is None:
                continue
            fee = round(impl[version].get(period, 0.0), 2)
            remainder = round(float(row["svc_rev"]) - fee, 2)
            if remainder < 0:
                raise ValueError(f"{version} {period}: implementation {fee} exceeds services revenue {row['svc_rev']}")
            row["impl_rev"] = fee
            row["rec_svc_rev"] = remainder
            log.append(f"{version} {period}: services {row['svc_rev']:,.2f} = implementation {fee:,.2f} + recurring {remainder:,.2f}")
    return log


def main(folder: str) -> None:
    impl = implementation_by_month(folder)
    for path in BOARD_FILES:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        a, b = _object_span(text, "TS_DATA")
        ts = json.loads(text[a:b])
        log = split_ts_data(ts, impl)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text[:a] + json.dumps(ts, separators=(",", ":")) + text[b:])
        print(path)
        print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1])
