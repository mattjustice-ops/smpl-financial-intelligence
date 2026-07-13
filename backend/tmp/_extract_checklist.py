import json
from pathlib import Path

path = Path(
    r"C:\Users\mattj\.cursor\projects\c-Users-mattj-cursor-projects-empty-window-saas-financial-intelligence\agent-transcripts\83aaaa1e-a6c9-4823-90b2-c589ba553448\83aaaa1e-a6c9-4823-90b2-c589ba553448.jsonl"
)
out = Path(__file__).with_name("_checklist_extract.txt")
want = {301, 302, 304, 1026, 1027, 1072, 1073, 1269, 1270, 1271, 1272, 1294, 1295, 1307}
chunks: list[str] = []
for i, line in enumerate(path.open(encoding="utf-8"), 1):
    if i not in want:
        continue
    obj = json.loads(line)
    texts = []
    for c in obj.get("message", {}).get("content", []):
        if isinstance(c, dict) and c.get("type") == "text":
            texts.append(c.get("text", ""))
    role = obj.get("role")
    chunks.append(f"===== LINE {i} role={role} =====\n" + "\n".join(texts)[:7000] + "\n")
out.write_text("\n".join(chunks), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
