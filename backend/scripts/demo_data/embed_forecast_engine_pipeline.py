"""Rebuild the Forecast Engine's built-in deal data (SRC.opp_pipeline, SRC.pipeline_book,
SRC.implementation_fees) from demo files.

The page shows this seed until the warehouse payload arrives; afterwards the same shapes come
from the deal and pipeline waterfall tables (app/services/reporting/pipeline_deals.py). Both are
built by the same code, so the seed and the live payload agree:
  * opp_pipeline: closed deals from Actual_opportunities.csv through the close month, open deals
    from Forecast_opportunities.csv (version Forecast) after it
  * pipeline_book: Actual_pipeline_waterfall.csv and Forecast_pipeline_waterfall.csv
  * implementation_fees: latest fee by segment from Actual_implementation_schedule.csv in
    <implementation_folder>

Only those keys of the `const SRC=` line change; the script stops if the line does not
round-trip unchanged before editing, or if any forecast month's weighted ARR moves by more
than $1 per deal type (forecast ARR is computed from it).

Usage:
  python embed_forecast_engine_pipeline.py <deal_folder> <implementation_folder> <close_month> <index.html> [...]
"""

from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from app.services.reporting.pipeline_deals import (  # noqa: E402
    implementation_fees_from_rows,
    pipeline_book_from_rows,
    pipeline_from_rows,
)

PREFIX = "const SRC="
TOLERANCE = 1.0


def _rows(folder: str, name: str) -> list[dict[str, str]]:
    with open(os.path.join(folder, name), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _forecast_version(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for r in rows if (r.get("version") or "Forecast") == "Forecast"]


def build(folder: str, close: str) -> tuple[dict, dict]:
    pipeline = pipeline_from_rows(
        _rows(folder, "Actual_opportunities.csv"),
        _forecast_version(_rows(folder, "Forecast_opportunities.csv")),
        as_of=close,
    )
    book = pipeline_book_from_rows(
        _rows(folder, "Actual_pipeline_waterfall.csv"),
        _forecast_version(_rows(folder, "Forecast_pipeline_waterfall.csv")),
        as_of=close,
    )
    return pipeline, book


def embed(path: str, pipeline: dict, book: dict, fees: dict, close: str) -> None:
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    idx = next(i for i, line in enumerate(lines) if line.startswith(PREFIX))
    body = lines[idx][len(PREFIX):]
    tail = body[len(body.rstrip().rstrip(";")):]
    src = json.loads(body.rstrip().rstrip(";"))
    if json.dumps(src, separators=(",", ":"), ensure_ascii=False) != body[: len(body) - len(tail)]:
        raise ValueError(f"{path}: SRC line does not round-trip; refusing to rewrite it")
    old = src.get("opp_pipeline", {})
    for period, by_type in pipeline.items():
        if period <= close:
            continue
        for deal_type, bucket in by_type.items():
            before = (old.get(period, {}).get(deal_type) or {}).get("weighted", 0)
            if abs(bucket["weighted"] - before) > TOLERANCE:
                raise ValueError(f"{period} {deal_type}: weighted {bucket['weighted']} vs built-in {before}")
    src["opp_pipeline"] = pipeline
    src["pipeline_book"] = book
    src["implementation_fees"] = fees
    lines[idx] = PREFIX + json.dumps(src, separators=(",", ":"), ensure_ascii=False) + tail
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


def main(folder: str, impl_folder: str, close: str, paths: list[str]) -> None:
    pipeline, book = build(folder, close)
    fees = implementation_fees_from_rows(_rows(impl_folder, "Actual_implementation_schedule.csv"))
    for path in paths:
        embed(path, pipeline, book, fees, close)
        print(f"{path}: {len(pipeline)} months, "
              f"{sum(b['count'] for m in pipeline.values() for b in m.values())} deals, "
              f"pipeline book {len(book)} months, implementation fees {fees}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
