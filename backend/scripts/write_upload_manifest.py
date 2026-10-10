"""Write the upload manifest (master_upload_order.csv) from the readiness registry and check datasets against it.

    python scripts/write_upload_manifest.py OUT_CSV [DATASET_DIR ...] [--allow-undeclared]

Every CSV in the dataset folders is matched to a manifest file. Exits 1 when a folder carries a file the
manifest does not declare, or the same file name twice, unless --allow-undeclared.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.readiness.manifest import MANIFEST_COLUMNS, check_files, manifest_rows  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out_csv", type=Path)
    ap.add_argument("dataset_dirs", nargs="*", type=Path)
    ap.add_argument("--allow-undeclared", action="store_true")
    args = ap.parse_args(argv)

    rows = manifest_rows()
    unrouted = [r["file_name"] for r in rows if not r["target_table"]]
    if unrouted:
        print(f"manifest files the loader has no route for: {', '.join(unrouted)}")
        return 1
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(MANIFEST_COLUMNS))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out_csv}: {len(rows)} files, {len({r['object_id'] for r in rows})} objects")
    if not args.dataset_dirs:
        return 0

    names = [p.name for d in args.dataset_dirs for p in sorted(d.glob("*.csv")) if p.resolve() != args.out_csv.resolve()]
    result = check_files(names)
    mapped: dict[str, str] = result["mapped"]  # type: ignore[assignment]
    print(f"checked {len(names)} files in {len(args.dataset_dirs)} folder(s): {len(mapped)} mapped to "
          f"{len(set(mapped.values()))} objects, {len(result['reference'])} reference")  # type: ignore[arg-type]
    for label in ("undeclared", "duplicates"):
        items = result[label]
        print(f"{label}: {', '.join(items) if items else 'none'}")  # type: ignore[arg-type]
    missing: dict[str, list[str]] = result["missing"]  # type: ignore[assignment]
    for oid, files in missing.items():
        print(f"not in this dataset: {oid}: {', '.join(files)}")
    failed = bool(result["undeclared"] or result["duplicates"])
    return 1 if failed and not args.allow_undeclared else 0


if __name__ == "__main__":
    raise SystemExit(main())
