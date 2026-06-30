"""Record a Neon storage_snapshot in usage_events (local / cron, no API key)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Record SMPL Ops storage snapshot to Neon")
    parser.add_argument("--force", action="store_true", help="Ignore 20h freshness guard")
    args = parser.parse_args()

    from app.db.session import SessionLocal
    from app.services.ops.storage_snapshot import maybe_collect_storage_snapshot

    db = SessionLocal()
    try:
        payload = maybe_collect_storage_snapshot(db, force=args.force)
    finally:
        db.close()

    if not payload:
        print("Storage snapshot failed.", file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "snapshot": payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
