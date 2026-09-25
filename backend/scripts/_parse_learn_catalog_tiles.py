"""Parse Skilljar catalog JSON embedded in learn_maxio_catalog_raw.html."""
from __future__ import annotations

import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
html = (BACKEND / "tmp" / "learn_maxio_catalog_raw.html").read_text(encoding="utf-8")

# Embedded object: {"PATH-...": {...}, "COURSE-...": {...}, ...}
m = re.search(
    r'<script[^>]*id=["\']SJ_searchTilesInternalUseOnlyAPISubjectToChange["\'][^>]*>\s*(\{.*?\})\s*</script>',
    html,
    re.I | re.S,
)
if not m:
    # Fallback: find first big JSON object with PATH- keys
    m = re.search(r'(\{"PATH-[^"]+":\s*\{.*?\})\s*</script>', html, re.S)
if not m:
    raise SystemExit("Could not find catalog tiles JSON")

raw = m.group(1)
tiles = json.loads(raw)
items = []
for key, val in tiles.items():
    if not isinstance(val, dict):
        continue
    items.append(
        {
            "key": key,
            "item_type": val.get("item_type"),
            "title": val.get("title"),
            "url": val.get("url"),
            "slug": val.get("slug"),
            "short_description": val.get("short_description") or "",
            "callout": val.get("callout") or "",
            "course_status": val.get("course_status") or "",
        }
    )

items.sort(key=lambda x: ((x.get("item_type") or ""), (x.get("title") or "").lower()))

# Priority keywords for SMPL connector / partner work
priority_rules = [
    ("P0", ("api", "developer", "webhook", "integrat", "advanced billing essentials")),
    ("P0", ("platform", "getting started", "onboarding essentials", "core objects")),
    ("P1", ("advanced billing", "self-service billing", "subscription")),
    ("P1", ("core essential", "core implementation", "finance reporting", "analytics reporting", "metrics", "mrr", "revenue recognition", "month-end")),
    ("P1", ("mcp",)),
    ("P2", ("salesforce", "quickbooks", "partner", "quote-to-cash", "importer", "data migration")),
    ("P3", ("webinar", "blog", "advocacy", "saaspedia")),
]


def score(item: dict) -> tuple[str, int]:
    blob = f"{item.get('title','')} {item.get('short_description','')}".lower()
    for pri, keys in priority_rules:
        if any(k in blob for k in keys):
            # lower number = higher priority within band
            return pri, 0 if pri == "P0" else 1 if pri == "P1" else 2 if pri == "P2" else 3
    return "P2", 5


for it in items:
    pri, _ = score(it)
    it["priority"] = pri

out = {
    "count": len(items),
    "by_type": {},
    "items": items,
    "prioritized": sorted(items, key=lambda x: (x["priority"], x.get("item_type") or "", x.get("title") or "")),
}
for it in items:
    t = it.get("item_type") or "?"
    out["by_type"][t] = out["by_type"].get(t, 0) + 1

path = BACKEND / "tmp" / "learn_maxio_catalog_courses.json"
path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"wrote {path} count={len(items)} types={out['by_type']}")
print("\n=== Prioritized (P0/P1 first) ===")
for it in out["prioritized"]:
    if it["priority"] in ("P0", "P1") or (
        it.get("item_type") in ("PATH", "COURSE") and "webinar" not in (it.get("title") or "").lower()
    ):
        print(f"{it['priority']} [{it.get('item_type')}] {it.get('title')} -> {it.get('url')}")
