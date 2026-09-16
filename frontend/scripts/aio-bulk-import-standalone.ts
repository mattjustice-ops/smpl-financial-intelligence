/**
 * Standalone bulk import — avoids next/server-only.
 *   npx tsx scripts/aio-bulk-import-standalone.ts tmp/aio_audits_capture.jsonl
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

import { evaluateManualAudit, DEFAULT_COMPETITORS, EVALUATOR_VERSION } from "../lib/aio/evaluate";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const input = process.argv[2];
if (!input) {
  console.error("Usage: npx tsx scripts/aio-bulk-import-standalone.ts <jsonl>");
  process.exit(1);
}

const pool = new pg.Pool({
  connectionString:
    process.env.AUTH_DATABASE_URL ||
    process.env.DATABASE_URL ||
    "postgresql://sfi:sfi_dev_password@localhost:5432/sfi",
});

const DDL = `
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS aio_queries (
  id TEXT PRIMARY KEY, query_text TEXT NOT NULL, category TEXT NOT NULL,
  intent TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 2,
  baseline_enabled BOOLEAN NOT NULL DEFAULT TRUE, target_topic TEXT,
  target_page_hint TEXT, notes TEXT, version INTEGER NOT NULL DEFAULT 1,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS aio_competitors (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  aliases_json JSONB NOT NULL DEFAULT '[]'::jsonb, active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS aio_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'manual_chatgpt', notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS aio_manual_audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID REFERENCES aio_batches(id) ON DELETE SET NULL,
  query_id TEXT REFERENCES aio_queries(id) ON DELETE SET NULL,
  query_text TEXT NOT NULL, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  product_note TEXT, raw_response TEXT NOT NULL,
  citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  clean_session_confirmed BOOLEAN NOT NULL DEFAULT FALSE, notes TEXT,
  evaluation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluator_version TEXT NOT NULL DEFAULT 'rules_v1', created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
`;

async function main() {
  await pool.query(DDL);
  const batchName =
    process.env.AIO_BATCH_NAME ||
    `Baseline bulk - ${new Date().toISOString().slice(0, 10)}`;
  const batch = await pool.query(
    `INSERT INTO aio_batches (name, source_type, notes) VALUES ($1,'manual_chatgpt',$2) RETURNING id`,
    [batchName, "ChatGPT Search temporary+unpersonalized bulk"],
  );
  const batchId = batch.rows[0].id;

  const lines = fs
    .readFileSync(path.resolve(input), "utf8")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  let ok = 0;
  for (const line of lines) {
    const rec = JSON.parse(line);
    const evaluation = evaluateManualAudit({
      query: rec.queryText,
      answer: rec.rawResponse,
      citationUrls: rec.citationUrls || [],
      competitors: [...DEFAULT_COMPETITORS],
    });
    await pool.query(
      `INSERT INTO aio_manual_audits (
        batch_id, query_id, query_text, product_note, raw_response,
        citations_json, clean_session_confirmed, notes, evaluation_json,
        evaluator_version, created_by
      ) VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9::jsonb,$10,$11)`,
      [
        batchId,
        rec.queryId || null,
        rec.queryText,
        "ChatGPT Search (consumer)",
        rec.rawResponse,
        JSON.stringify(rec.citationUrls || []),
        true,
        rec.notes || "",
        JSON.stringify(evaluation),
        EVALUATOR_VERSION,
        "bulk-import-standalone",
      ],
    );
    ok += 1;
    console.log(
      `${ok}/${lines.length} ${rec.queryId} mentioned=${evaluation.smpl_mentioned} ${evaluation.recommendation_strength}`,
    );
  }
  console.log(`Imported ${ok} into batch ${batchId} (${batchName})`);
  await pool.end();
}

main().catch(async (e) => {
  console.error(e);
  await pool.end();
  process.exit(1);
});
