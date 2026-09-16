/**
 * Bulk-import manual ChatGPT Search audits into local aio_* tables.
 *
 * Usage:
 *   node scripts/aio-bulk-import.mjs path/to/audits.jsonl
 *   node scripts/aio-bulk-import.mjs path/to/audits.json
 *
 * Each record:
 *   { "queryId"?: string, "queryText": string, "rawResponse": string,
 *     "citationUrls"?: string[], "notes"?: string, "batchName"?: string }
 *
 * Or JSON array of the same shape.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import pg from "pg";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const require = createRequire(import.meta.url);

// Load evaluate via tsx-compiled path isn't available; call API instead if
// NEXT is up, else use dynamic import of built logic by spawning tsx.

const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: node scripts/aio-bulk-import.mjs <audits.json|jsonl>");
  process.exit(1);
}

const abs = path.resolve(inputPath);
const raw = fs.readFileSync(abs, "utf8");
let records;
if (abs.endsWith(".jsonl")) {
  records = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l));
} else {
  const parsed = JSON.parse(raw);
  records = Array.isArray(parsed) ? parsed : parsed.audits || [];
}

if (!records.length) {
  console.error("No audit records found");
  process.exit(1);
}

const batchName =
  process.env.AIO_BATCH_NAME ||
  `Baseline bulk - ${new Date().toISOString().slice(0, 10)}`;

const base = process.env.AIO_BASE_URL || "http://127.0.0.1:3002";

// Prefer HTTP through the running Next app (uses same evaluator + schema).
// Requires a session cookie in AIO_COOKIE, or we fall back to direct Postgres
// note: without cookie, API returns 401 — then print instructions.

async function postViaApi(rec) {
  const headers = { "Content-Type": "application/json" };
  if (process.env.AIO_COOKIE) headers.Cookie = process.env.AIO_COOKIE;
  const r = await fetch(`${base}/api/aio/audits`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      queryId: rec.queryId || null,
      queryText: rec.queryText || rec.query_text,
      rawResponse: rec.rawResponse || rec.raw_response || rec.answer,
      citationUrls: rec.citationUrls || rec.citations || [],
      notes: rec.notes || "",
      cleanSessionConfirmed: rec.cleanSessionConfirmed !== false,
      batchName: rec.batchName || batchName,
      productNote: rec.productNote || "ChatGPT Search (consumer)",
    }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(j.detail || `HTTP ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return j.audit;
}

let ok = 0;
let fail = 0;
for (const [i, rec] of records.entries()) {
  const q = rec.queryText || rec.query_text || rec.query || "";
  try {
    const audit = await postViaApi(rec);
    ok += 1;
    const e = audit.evaluation_json || {};
    console.log(
      `[${i + 1}/${records.length}] OK ${rec.queryId || ""} mention=${e.smpl_mentioned} ${e.recommendation_strength}`,
    );
  } catch (e) {
    fail += 1;
    console.error(`[${i + 1}/${records.length}] FAIL ${q.slice(0, 60)}: ${e.message}`);
    if (e.status === 401 || e.status === 403) {
      console.error(
        "\nAPI requires ops-admin session. In Chrome DevTools on localhost:3002, copy Cookie header and:\n  $env:AIO_COOKIE='...'; node scripts/aio-bulk-import.mjs ...\n",
      );
      process.exit(1);
    }
  }
}

console.log(`Done. ok=${ok} fail=${fail} batch=${batchName}`);
