/**
 * Build capture record from stdin JSON and POST.
 * stdin: { queryId, queryText, rawResponse, citationUrls?, batchName? }
 * Usage: Get-Content rec.json -Raw | node scripts/aio-post-json.mjs
 *    or: node scripts/aio-post-json.mjs path/to/rec.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let raw = process.argv[2]
  ? fs.readFileSync(path.resolve(process.argv[2]), "utf8")
  : fs.readFileSync(0, "utf8");
const p = JSON.parse(raw);
const rec = {
  queryId: p.queryId,
  queryText: p.queryText,
  rawResponse: p.rawResponse || (p.chunks || []).join(""),
  citationUrls: p.citationUrls || [],
  notes: p.notes || "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  batchName: p.batchName || "Full 46 - 2026-09-23",
  capturedAt: new Date().toISOString(),
};
if (!rec.queryId || !rec.queryText || !rec.rawResponse) {
  console.error("Need queryId, queryText, rawResponse|chunks");
  process.exit(1);
}
fs.writeFileSync(path.join(root, "tmp", "_last_capture.json"), JSON.stringify(rec));
const r = await fetch("http://127.0.0.1:3847/capture", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(rec),
});
const j = await r.json();
console.log(
  JSON.stringify({
    ok: r.ok,
    ...j,
    len: rec.rawResponse.length,
    smpl: /smpl/i.test(rec.rawResponse),
    queryId: rec.queryId,
  }),
);
