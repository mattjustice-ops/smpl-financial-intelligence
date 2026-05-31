"""Pre-flight check: workforce routes including /validation exist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "app" / "main.py"
REQUIRED = (
    "/api/v1/workforce/ping",
    "/api/v1/workforce/plan",
    "/api/v1/workforce/plan-debug",
    "/api/v1/workforce/recompute",
    "/api/v1/workforce/validation",
    "/api/v1/workforce/feeds/payroll",
    "/api/v1/workforce/feeds/cash-payroll",
    "/api/v1/workforce/feeds/gtm-capacity",
)


def main() -> int:
    if not MAIN.is_file():
        print(f"FAIL: missing {MAIN}", file=sys.stderr)
        return 1
    source = MAIN.read_text(encoding="utf-8")
    match = re.search(r'WORKFORCE_BUILD_ID\s*=\s*"([^"]+)"', source)
    if not match:
        print("FAIL: WORKFORCE_BUILD_ID not found in app/main.py", file=sys.stderr)
        return 1
    if "/api/v1/workforce/ping" not in source:
        print("FAIL: inline /api/v1/workforce/ping not in app/main.py", file=sys.stderr)
        return 1
    if "/api/v1/workforce/plan-debug" not in source:
        print("FAIL: inline /api/v1/workforce/plan-debug not in app/main.py", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT))
    try:
        from app.main import WORKFORCE_BUILD_ID, app  # noqa: WPS433
    except Exception as exc:
        print(f"IMPORT_FAIL: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    print(f"workforce_build_id={WORKFORCE_BUILD_ID}")
    paths = {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")}
    missing = [p for p in REQUIRED if p not in paths]
    wf = sorted(p for p in paths if "/workforce" in p)
    print("workforce_paths=" + str(wf))
    if missing:
        print("FAIL: missing workforce routes: " + ", ".join(missing), file=sys.stderr)
        return 1
    print("VERIFY_WORKFORCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
