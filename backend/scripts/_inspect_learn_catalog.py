"""Inspect learn.maxio catalog HTML for embedded course titles."""
from __future__ import annotations

import json
import re
from pathlib import Path

html = Path("backend/tmp/learn_maxio_catalog_raw.html").read_text(encoding="utf-8")
print("len", len(html))
print("has login form", 'id="login_form"' in html)
print("course-catalog string count", html.lower().count("course"))

scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.I | re.S)
print("scripts", len(scripts))
for i, s in enumerate(scripts):
    low = s.lower()
    if any(k in low for k in ("course", "catalog", "curriculum", "lesson", "path")) and len(s) > 200:
        print("--- script", i, "len", len(s))
        print(s[:800].replace("\n", " ")[:800])

# titles in quotes near api/billing/etc
titles = re.findall(r'"title"\s*:\s*"([^"\\]{5,160})"', html)
print("json title count", len(titles))
for t in titles[:80]:
    print(" TITLE:", t)

names = re.findall(r'"name"\s*:\s*"([^"\\]{5,160})"', html)
interesting = [
    n
    for n in names
    if any(
        k in n.lower()
        for k in (
            "api",
            "billing",
            "core",
            "integrat",
            "report",
            "partner",
            "developer",
            "mrr",
            "revenue",
            "webhook",
            "chargify",
            "saasoptics",
            "maxio",
            "subscription",
            "invoice",
            "finance",
            "academy",
            "platform",
            "getting started",
        )
    )
]
print("interesting names", len(interesting))
for n in interesting[:100]:
    print(" NAME:", n)

# visible text blocks
idx = html.lower().find("all courses")
print("all courses idx", idx)
if idx >= 0:
    Path("backend/tmp/learn_maxio_catalog_snippet.txt").write_text(html[idx : idx + 5000], encoding="utf-8")
    print("wrote snippet")

# hrefs with /course or /path
hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
course_hrefs = [h for h in hrefs if re.search(r"/(course|path|series|programs?)/", h, re.I)]
print("course hrefs", len(course_hrefs))
for h in list(dict.fromkeys(course_hrefs))[:50]:
    print(" HREF:", h)

out = {
    "json_titles": titles[:200],
    "interesting_names": interesting[:200],
    "course_hrefs": list(dict.fromkeys(course_hrefs))[:200],
}
Path("backend/tmp/learn_maxio_catalog_parsed.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print("wrote backend/tmp/learn_maxio_catalog_parsed.json")
