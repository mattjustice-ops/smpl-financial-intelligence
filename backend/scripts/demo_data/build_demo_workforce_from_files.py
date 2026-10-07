"""Rebuild the Board demo Workforce data (WF_DEMO) from the same files that are loaded into the warehouse.

Runs the Board Workforce payload builder the API uses over the files: the Employees roster for
head counts, the GL detail for payroll, the headcount plan for quota capacity, the open
requisitions and the hiring ramp assumptions.

Usage:
  python build_demo_workforce_from_files.py <gl_dir> <files_dir> <board_html> [<board_html> ...] [--close YYYY-MM] [--write]

Default is a dry run that prints the summary and the roster cost vs GL payroll check. ``--write``
replaces the ``var WF_DEMO=`` line in each Board page.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.reporting.board_workforce import workforce_board_payload  # noqa: E402
from app.services.workforce.gl_payroll import build_gl_payroll, with_actual_fallback  # noqa: E402
from app.services.workforce.legacy_headcount import _snapshot_from_mapping  # noqa: E402
from app.services.workforce.roster import employee_from_loaded_row  # noqa: E402

WF_LINE = re.compile(r"^(\s*var WF_DEMO=)(\{.*\})(;?\s*)$")


def _read(path: str) -> list[dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _plan(path: str, year: str) -> list:
    rows = [_snapshot_from_mapping(r) for r in _read(path)]
    return [r for r in rows if r is not None and f"{r.period:%Y}" == year]


def build(gl_dir: str, files_dir: str, close: str) -> dict:
    year = close[:4]
    gl = {v: build_gl_payroll(_read(os.path.join(gl_dir, f"{v}_gl_detail.csv"))) for v in ("Actual", "Forecast")}
    ramp = [
        {"ramp_months": r["ramp_months"], "month": r["month_after_start"], "pct": r["productivity_pct"]}
        for r in _read(os.path.join(files_dir, "Hiring_Ramp_Assumptions.csv"))
    ]
    return workforce_board_payload(
        as_of_period=close,
        roster=[employee_from_loaded_row(r) for r in _read(os.path.join(files_dir, "Forecast_Employees.csv"))],
        budget_roster=[employee_from_loaded_row(r) for r in _read(os.path.join(files_dir, "Budget_Employees.csv"))],
        plan=_plan(os.path.join(files_dir, "Forecast_Headcount_Plan.csv"), year),
        budget_plan=_plan(os.path.join(files_dir, "Budget_Headcount_Plan.csv"), year),
        payroll=with_actual_fallback(gl["Forecast"], gl["Actual"]),
        reqs=_read(os.path.join(files_dir, "Forecast_Open_Requisitions.csv")),
        ramp=ramp,
        roster_source="forecast_employees",
    )


def _report(payload: dict, plan_heads: dict) -> list[str]:
    notes = []
    s = payload["summary"]
    print(f"heads start {s['start_hc']}  close {s['close_hc']}  dec {s['dec_hc']}  budget close {s['budget_close_hc']}")
    print(f"open reqs after close {s['open_reqs']}  roster rows {len(payload['roster'])}")
    print("heads by month", payload["heads_total"])
    print("GL payroll by month", [round(v) if v is not None else None for v in payload["payroll"]])
    print("payroll teams", list(payload["payroll_by_team"]))
    print("quota by month", payload["quota"])
    print("ramp curves", payload["ramp"])
    check = payload["payroll_check"]
    print(f"roster cost vs GL payroll ({check['span']}):")
    for r in check["rows"]:
        print(f"  {r['team']:18} roster {r['roster']:>14,.0f}  GL {r['gl']:>14,.0f}  variance {r['variance']:>14,.0f}")
    for i, (got, want) in enumerate(zip(payload["heads_total"], plan_heads.get("total", []))):
        if got != want:
            notes.append(f"FAIL heads {payload['months'][i]} roster {got} vs headcount plan {want}")
    if any(v is None for v in payload["payroll"]):
        notes.append("FAIL months without GL payroll: " + ", ".join(m for m, v in zip(payload["months"], payload["payroll"]) if v is None))
    return notes


def main(argv: list[str]) -> int:
    write = "--write" in argv
    close = "2026-06"
    args = []
    it = iter(a for a in argv if a != "--write")
    for a in it:
        if a == "--close":
            close = next(it)
        else:
            args.append(a)
    if len(args) < 3:
        print(__doc__)
        return 2
    gl_dir, files_dir, pages = args[0], args[1], args[2:]
    payload = build(gl_dir, files_dir, close)
    plan = _plan(os.path.join(files_dir, "Forecast_Headcount_Plan.csv"), close[:4])
    totals: dict[str, int] = {}
    for r in plan:
        totals[f"{r.period:%Y-%m}"] = totals.get(f"{r.period:%Y-%m}", 0) + int(r.headcount_ending)
    notes = _report(payload, {"total": [totals.get(m) for m in payload["months"]]})
    for n in notes:
        print(n)
    if notes:
        print("== checks FAILED; nothing written")
        return 1
    print("== checks passed (roster heads tie to the headcount plan; GL payroll in every month)")
    if not write:
        print("== dry run; nothing written")
        return 0
    line = json.dumps(payload, separators=(",", ":"))
    for page in pages:
        with open(page, encoding="utf-8") as f:
            lines = f.read().split("\n")
        hits = [i for i, ln in enumerate(lines) if WF_LINE.match(ln)]
        if len(hits) != 1:
            raise SystemExit(f"expected one 'var WF_DEMO=' line in {page}, found {len(hits)}")
        m = WF_LINE.match(lines[hits[0]])
        lines[hits[0]] = m.group(1) + line + m.group(3)
        with open(page, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
        print("wrote", page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
