"""Reload Actual_MRR_Waterfall.csv into Neon prod for one org (full snapshot replace)."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))


def _load_prod_database_url() -> None:
    from scripts.local_db_url import normalize_database_url, validate_database_url

    if os.environ.get("DATABASE_URL", "").strip():
        validate_database_url(os.environ["DATABASE_URL"])
        os.environ["DATABASE_URL"] = normalize_database_url(os.environ["DATABASE_URL"])
        return

    env_file = REPO_ROOT / "frontend" / ".env.neon-production.local"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                validate_database_url(raw)
                os.environ["DATABASE_URL"] = normalize_database_url(raw)
                return
    raise SystemExit("Set DATABASE_URL or frontend/.env.neon-production.local")


_load_prod_database_url()

from app.db.session import SessionLocal  # noqa: E402
from app.services.demo_csv.loader import load_demo_csv_core  # noqa: E402
from app.services.ops.warehouse_health import assess_warehouse_readiness  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organization-id", default="8571e520-0687-4516-bdee-379f37c58c1f")
    parser.add_argument(
        "--csv",
        default=str(Path.home() / "OneDrive/Documents/simple CSVS/Actual_MRR_Waterfall.csv"),
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    org_id = uuid.UUID(args.organization_id.strip())
    content = csv_path.read_bytes()

    with SessionLocal() as db:
        before = assess_warehouse_readiness(db, org_id)
        print(f"Before: ok={before['ok']} periods={before['actual_mrr_periods']} issues={before['issues']}")

        res = load_demo_csv_core(db, org_id, content, filename=csv_path.name)
        if not res.did_upsert:
            db.rollback()
            raise SystemExit(f"Load failed: {res.integrity_error or res.header_error}")
        db.commit()
        print(f"Loaded {res.rows_upserted} rows into {res.csv_kind}")

        after = assess_warehouse_readiness(db, org_id)
        print(f"After: ok={after['ok']} periods={after['actual_mrr_periods']} issues={after['issues']}")
        if not after["ok"]:
            sys.exit(1)
    print("Board warehouse ready.")


if __name__ == "__main__":
    main()
