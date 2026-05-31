"""Pre-flight check: Management PL routes exist. Run from backend/ directory."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "app" / "main.py"


def _read_build_id() -> str | None:
    if not MAIN.is_file():
        return None
    source = MAIN.read_text(encoding="utf-8")
    match = re.search(r'SFI_BUILD_ID\s*=\s*"([^"]+)"', source)
    return match.group(1) if match else None


def main() -> int:
    if not MAIN.is_file():
        print(f"FAIL: missing {MAIN}", file=sys.stderr)
        return 1

    source = MAIN.read_text(encoding="utf-8")
    build_id = _read_build_id()
    if not build_id:
        print("FAIL: SFI_BUILD_ID not found in app/main.py", file=sys.stderr)
        return 1
    if "management-pl/ping" not in source:
        print("FAIL: management-pl/ping route not in app/main.py", file=sys.stderr)
        return 1

    print(f"SFI_BUILD_ID={build_id}")
    print("file_check=OK")

    sys.path.insert(0, str(ROOT))
    try:
        from app.main import SFI_BUILD_ID, app  # noqa: WPS433
    except Exception as exc:
        print(f"IMPORT_FAIL: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    if SFI_BUILD_ID != build_id:
        print(f"FAIL: runtime SFI_BUILD_ID {SFI_BUILD_ID!r} != file {build_id!r}", file=sys.stderr)
        return 1

    paths = sorted({getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")})
    mpl = [p for p in paths if "management-pl" in p]
    print("SFI_BUILD_ID=" + SFI_BUILD_ID)
    print("management_paths=" + str(mpl))
    if not mpl:
        print("FAIL: no management-pl routes on app", file=sys.stderr)
        return 1

    print("VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
