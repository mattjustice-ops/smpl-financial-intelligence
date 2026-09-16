/**
 * Flush pending capture: tmp/aio_pending.json
 * { queryId, queryText, b64Chunks: string[] }
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pendingPath = path.join(root, "tmp", "aio_pending.json");
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");

const pending = JSON.parse(fs.readFileSync(pendingPath, "utf8"));
const text = Buffer.from(pending.b64Chunks.join(""), "base64").toString("utf8");
const rec = {
  queryId: pending.queryId,
  queryText: pending.queryText,
  rawResponse: text,
  citationUrls: pending.citationUrls || [],
  notes: pending.notes || "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  capturedAt: new Date().toISOString(),
};
fs.appendFileSync(capturePath, JSON.stringify(rec) + "\n");
const p = fs.existsSync(progressPath)
  ? JSON.parse(fs.readFileSync(progressPath, "utf8"))
  : { done: [], failed: [] };
if (!p.done.includes(rec.queryId)) p.done.push(rec.queryId);
p.updatedAt = new Date().toISOString();
fs.writeFileSync(progressPath, JSON.stringify(p, null, 2));
console.log(`flushed ${rec.queryId} len=${text.length} done=${p.done.length}`);
