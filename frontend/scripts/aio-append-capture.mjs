/**
 * Append one captured audit + update progress.
 * Usage: node scripts/aio-append-capture.mjs <queryId> <jsonFileWithAnswer>
 * Or stdin JSON: { queryId, queryText, rawResponse, citationUrls }
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");

const payload = JSON.parse(fs.readFileSync(0, "utf8"));
if (!payload.queryId || !payload.queryText || !payload.rawResponse) {
  console.error("Need queryId, queryText, rawResponse");
  process.exit(1);
}

fs.mkdirSync(path.dirname(capturePath), { recursive: true });
fs.appendFileSync(
  capturePath,
  JSON.stringify({
    queryId: payload.queryId,
    queryText: payload.queryText,
    rawResponse: payload.rawResponse,
    citationUrls: payload.citationUrls || [],
    notes: payload.notes || "temporary+unpersonalized+web_search",
    cleanSessionConfirmed: true,
    capturedAt: new Date().toISOString(),
  }) + "\n",
);

let progress = { done: [], failed: [] };
if (fs.existsSync(progressPath)) {
  progress = JSON.parse(fs.readFileSync(progressPath, "utf8"));
}
if (!progress.done.includes(payload.queryId)) progress.done.push(payload.queryId);
progress.updatedAt = new Date().toISOString();
fs.writeFileSync(progressPath, JSON.stringify(progress, null, 2));
console.log(`appended ${payload.queryId}; done=${progress.done.length}`);
