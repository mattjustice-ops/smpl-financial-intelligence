/**
 * Save + import one audit from tmp/aio_chunks.json
 * Shape: { queryId, queryText, b64Chunks: string[] }
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pending = JSON.parse(
  fs.readFileSync(path.join(root, "tmp", "aio_chunks.json"), "utf8"),
);
const text = Buffer.from(pending.b64Chunks.join(""), "base64").toString("utf8");
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");
const onePath = path.join(root, "tmp", "aio_one.jsonl");

const rec = {
  queryId: pending.queryId,
  queryText: pending.queryText,
  rawResponse: text,
  citationUrls: [],
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

process.env.AIO_BATCH_NAME =
  process.env.AIO_BATCH_NAME || "Baseline bulk - 2026-09-15";
const r = spawnSync(
  "npx",
  ["--yes", "tsx", "scripts/aio-bulk-import-standalone.ts", "tmp/aio_one.jsonl"],
  { cwd: root, env: process.env, encoding: "utf8", shell: true },
);
process.stdout.write(r.stdout || "");
process.stderr.write(r.stderr || "");
console.log(
  `saved+import ${rec.queryId} len=${text.length} done=${p.done.length} exit=${r.status}`,
);
process.exit(r.status ?? 1);
