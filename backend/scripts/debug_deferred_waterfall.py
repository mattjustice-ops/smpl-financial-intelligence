"""Run locally: python scripts/debug_deferred_waterfall.py [organization_id]"""

from __future__ import annotations

import sys
import traceback
import uuid

from app.db.session import SessionLocal
from app.services.dashboard.waterfall_service import waterfall_response

ORG_DEFAULT = "8571e520-0687-4516-bdee-379f37c58c1f"


def main() -> None:
    org_id = uuid.UUID(sys.argv[1] if len(sys.argv) > 1 else ORG_DEFAULT)
    db = SessionLocal()
    try:
        result = waterfall_response(
            db,
            org_id,
            waterfall_name="deferred_revenue",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            marketing_channel=None,
            region=None,
            segment=None,
            owner=None,
            waterfall_type=None,
        )
        print(f"OK: {len(result.rows)} summary rows, {len(result.validation)} validation checks")
    except Exception:
        traceback.print_exc()
        raise SystemExit(1) from None
    finally:
        db.close()


if __name__ == "__main__":
    main()
