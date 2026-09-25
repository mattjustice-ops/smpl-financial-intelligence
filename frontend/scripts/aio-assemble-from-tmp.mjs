/**
 * Save CDP-exported chunks then post capture.
 * Expects:
 *   tmp/aio_chunk_meta.json  { queryId, queryText, n, batchName? }
 *   tmp/aio_chunk_000.txt ... aio_chunk_(n-1).txt
 *
 * Usage: node scripts/aio-assemble-from-tmp.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const metaPath = path.join(root, "tmp", "aio_chunk_meta.json");
const meta = JSON.parse(fs.readFileSync(metaPath, "utf8"));
const parts = [];
for (let i = 0; i < meta.n; i++) {
  const p = path.join(root, "tmp", `aio_chunk_${String(i).padStart(3, "0")}.txt`);
  parts.push(fs.readFileSync(p, "utf8"));
}
const rec = {
  queryId: meta.queryId,
  queryText: meta.queryText,
  rawResponse: parts.join(""),
  citationUrls: meta.citationUrls || [],
  notes: "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  batchName: meta.batchName || "Full 46 - 2026-09-23",
  capturedAt: new Date().toISOString(),
};
const out = path.join(root, "tmp", "_last_capture.json");
fs.writeFileSync(out, JSON.stringify(rec));
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
