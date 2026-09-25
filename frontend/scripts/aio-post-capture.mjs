/**
 * POST one capture record to local capture server + append jsonl.
 * Usage: node scripts/aio-post-capture.mjs path/to/record.json
 * Record: { queryId, queryText, rawResponse, citationUrls? }
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const file = process.argv[2];
if (!file) {
  console.error("Usage: node scripts/aio-post-capture.mjs <record.json>");
  process.exit(1);
}
const rec = JSON.parse(fs.readFileSync(path.resolve(file), "utf8"));
if (!rec.queryId || !rec.queryText || !rec.rawResponse) {
  console.error("Need queryId, queryText, rawResponse");
  process.exit(1);
}
const body = {
  queryId: rec.queryId,
  queryText: rec.queryText,
  rawResponse: rec.rawResponse,
  citationUrls: rec.citationUrls || [],
  notes: rec.notes || "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  batchName: rec.batchName || "Full 46 - 2026-09-23",
  capturedAt: new Date().toISOString(),
};
const r = await fetch("http://127.0.0.1:3847/capture", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const j = await r.json();
console.log(JSON.stringify({ ok: r.ok, ...j, len: body.rawResponse.length, smpl: /smpl/i.test(body.rawResponse) }));
