/**
 * Save pending capture from stdin JSON:
 * { queryId, queryText, b64Chunks: string[] }
 * Then write one-line jsonl for import.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pending = JSON.parse(fs.readFileSync(0, "utf8"));
const text = Buffer.from((pending.b64Chunks || []).join(""), "base64").toString("utf8");
if (!pending.queryId || !pending.queryText || !text) {
  console.error("bad pending");
  process.exit(1);
}
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");
const onePath = path.join(root, "tmp", "aio_one.jsonl");
const rec = {
  queryId: pending.queryId,
  queryText: pending.queryText,
  rawResponse: text,
  citationUrls: pending.citationUrls || [],
  notes: "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  capturedAt: new Date().toISOString(),
};
fs.appendFileSync(capturePath, JSON.stringify(rec) + "\n");
fs.writeFileSync(onePath, JSON.stringify(rec) + "\n");
const p = fs.existsSync(progressPath)
  ? JSON.parse(fs.readFileSync(progressPath, "utf8"))
  : { done: [], failed: [] };
if (!p.done.includes(rec.queryId)) p.done.push(rec.queryId);
p.updatedAt = new Date().toISOString();
fs.writeFileSync(progressPath, JSON.stringify(p, null, 2));
console.log(`saved ${rec.queryId} len=${text.length} done=${p.done.length}`);
