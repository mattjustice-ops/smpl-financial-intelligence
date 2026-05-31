"""Debug workforce plan build — writes traceback to debug_workforce_plan.out"""

from __future__ import annotations

import sys
import traceback
import uuid
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND / "debug_workforce_plan.out"
sys.path.insert(0, str(BACKEND))

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")


def main() -> int:
    lines: list[str] = []
    try:
        from app.db.session import SessionLocal
        from app.services.workforce import service
        from app.services.workforce.schemas import WorkforcePlanResponse

        db = SessionLocal()
        try:
            plan = service.build_workforce_plan(
                db,
                ORG,
                scenario="Actual",
                start_period=date(2026, 5, 1),
                end_period=date(2026, 5, 31),
                persist=False,
            )
            lines.append(f"build_ok rows={len(plan.period_summary)}")
            # Response validation (same as FastAPI response_model)
            WorkforcePlanResponse.model_validate(plan.model_dump())
            lines.append("response_validate_ok")
        finally:
            db.close()
    except Exception:
        lines.append(traceback.format_exc())
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)
    return 0 if lines[-1] == "response_validate_ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
