"""One-shot: reopen Validation Engine mapping for account 6105 (AI Infrastructure).

Usage (from repo root, with backend venv + DATABASE_URL):
  python backend/scripts/unmap_ai_infrastructure_6105.py
  python backend/scripts/unmap_ai_infrastructure_6105.py --period 2026-06
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / "frontend" / ".env.local", override=False)

# SQLAlchemy + psycopg3 (venv has psycopg, not psycopg2)
_url = os.getenv("DATABASE_URL", "")
if _url.startswith("postgresql://"):
    os.environ["DATABASE_URL"] = "postgresql+psycopg://" + _url[len("postgresql://") :]
elif _url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = "postgresql+psycopg://" + _url[len("postgres://") :]

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.close_context_blob import CloseContextBlob  # noqa: E402
from app.services.validation_engine import unmap_account  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2026-06")
    parser.add_argument("--account-id", default="6105")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL missing", file=sys.stderr)
        return 1

    db: Session = SessionLocal()
    try:
        blobs = db.scalars(
            select(CloseContextBlob).where(CloseContextBlob.as_of_period == args.period)
        ).all()
        touched = 0
        for blob in blobs:
            sections = blob.sections_json if isinstance(blob.sections_json, dict) else {}
            queue = sections.get("mapping_queue") or []
            if not isinstance(queue, list):
                continue
            hit = next(
                (
                    q
                    for q in queue
                    if isinstance(q, dict)
                    and str(q.get("account_id") or q.get("account_number") or "") == args.account_id
                    and q.get("status") in ("mapped", "excluded")
                ),
                None,
            )
            if not hit:
                continue
            print(
                json.dumps(
                    {
                        "organization_id": str(blob.organization_id),
                        "as_of_period": args.period,
                        "account_id": args.account_id,
                        "name": hit.get("name"),
                        "status": hit.get("status"),
                        "mapped_to": hit.get("mapped_to"),
                    },
                    indent=2,
                )
            )
            if args.dry_run:
                continue
            unmap_account(
                db,
                blob.organization_id,
                args.period,
                account_id=args.account_id,
                unmapped_by="owner_fix",
            )
            touched += 1
            print(f"Reopened {args.account_id} for org {blob.organization_id}")
        if touched == 0 and not args.dry_run:
            print(f"No mapped/excluded {args.account_id} rows found for {args.period}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
