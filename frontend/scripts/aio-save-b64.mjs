import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [,, queryId, queryText, b64Path] = process.argv;
if (!queryId || !queryText || !b64Path) {
  console.error("Usage: node aio-save-b64.mjs <queryId> <queryText> <b64file>");
  process.exit(1);
}
const text = Buffer.from(fs.readFileSync(b64Path, "utf8").trim(), "base64").toString("utf8");
const capturePath = path.join(root, "tmp", "aio_audits_capture.jsonl");
const progressPath = path.join(root, "tmp", "aio_run_progress.json");
const rec = {
  queryId,
  queryText,
  rawResponse: text,
  citationUrls: [],
  notes: "temporary+unpersonalized+web_search",
  cleanSessionConfirmed: true,
  capturedAt: new Date().toISOString(),
};
fs.appendFileSync(capturePath, JSON.stringify(rec) + "\n");
const p = fs.existsSync(progressPath)
  ? JSON.parse(fs.readFileSync(progressPath, "utf8"))
  : { done: [], failed: [] };
if (!p.done.includes(queryId)) p.done.push(queryId);
p.updatedAt = new Date().toISOString();
fs.writeFileSync(progressPath, JSON.stringify(p, null, 2));
console.log(`saved ${queryId} len=${text.length} done=${p.done.length}`);
