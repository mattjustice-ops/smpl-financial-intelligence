"""Night-before / ops freeze pre-warm (local or cron via API preferred).

Preferred schedule (Railway / Task Scheduler) hits the API so workers share auth:

  curl -X POST "$SFI_PUBLIC_API_URL/api/v1/ops/prewarm-freeze" \\
    -H "X-Smpl-Internal-Key: $BILLING_INTERNAL_API_KEY"

This CLI talks to the warehouse DB directly (no HTTP) — useful for local dry-runs.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prewarm close-context freeze packs")
    parser.add_argument("--dry-run", action="store_true", help="List orgs/periods only")
    parser.add_argument("--organization-id", default=None, help="Optional single org UUID")
    args = parser.parse_args()

    from app.db.session import SessionLocal
    from app.services.close_context.freeze_blob_service import prewarm_freeze_blobs

    org_id = uuid.UUID(args.organization_id) if args.organization_id else None
    db = SessionLocal()
    try:
        payload = prewarm_freeze_blobs(
            db,
            organization_id=org_id,
            dry_run=args.dry_run,
        )
    finally:
        db.close()

    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
