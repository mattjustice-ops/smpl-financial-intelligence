/**
 * Imports a ChatGPT capture-v2 run (chatgpt-capture-v2.browser.js output) into the AIO tables.
 * Benchmark answers go into one checkpoint batch; priority repeats go into a separate batch
 * with source_type manual_chatgpt_repeat so "latest answer per query" views ignore them.
 *
 *   npx tsx scripts/aio/import-capture-v2.ts <capture jsonl>
 *   env: AIO_BATCH_NAME, AIO_REPEAT_BATCH_NAME (defaults derive from the run date)
 */
import fs from "node:fs";
import path from "node:path";
import pg from "pg";

import { REPEAT_SOURCE_TYPE } from "../../lib/aio/checkpoints";
import { DEFAULT_COMPETITORS, EVALUATOR_VERSION, evaluateManualAudit } from "../../lib/aio/evaluate";
import { isInterfaceUrl } from "../../lib/aio/visibility-score";

type Capture = {
  schema: string;
  runId: string;
  key: string;
  queryId: string;
  queryText: string;
  trial: number | null;
  phase: string;
  sentAt: string;
  conversationUrl?: string;
  environment?: Record<string, unknown>;
  answerText?: string;
  proseText?: string;
  citationLabels?: string[];
  sources?: Array<{ url: string; title?: string | null; publisher?: string | null; paragraph?: string | null; hidden?: boolean }>;
  citationStatus?: string;
  error?: string;
};

const input = process.argv[2];
if (!input) {
  console.error("Usage: npx tsx scripts/aio/import-capture-v2.ts <capture jsonl>");
  process.exit(1);
}

const pool = new pg.Pool({
  connectionString:
    process.env.AUTH_DATABASE_URL || process.env.DATABASE_URL || "postgresql://sfi:sfi_dev_password@localhost:5432/sfi",
});

async function main() {
  const captures: Capture[] = fs
    .readFileSync(path.resolve(input), "utf8")
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
  const bad = captures.filter((c) => c.schema !== "aio_capture_v2");
  if (bad.length) throw new Error(`${bad.length} records are not aio_capture_v2`);
  const runDate = captures.map((c) => c.sentAt).filter(Boolean).sort()[0]?.slice(0, 10) ?? "unknown-date";
  const benchName = process.env.AIO_BATCH_NAME || `Full 46 - ${runDate} controlled rerun (v2)`;
  const repeatName = process.env.AIO_REPEAT_BATCH_NAME || `Priority repeats - ${runDate} controlled rerun (v2)`;

  await pool.query(`ALTER TABLE aio_manual_audits ADD COLUMN IF NOT EXISTS capture_json JSONB`);
  const existing = await pool.query(`SELECT name FROM aio_batches WHERE name = ANY($1::text[])`, [[benchName, repeatName]]);
  if (existing.rowCount) {
    throw new Error(`Batch already imported: ${existing.rows.map((r) => r.name).join(", ")}`);
  }
  const knownIds = new Set(
    (await pool.query(`SELECT id FROM aio_queries`)).rows.map((r: { id: string }) => r.id),
  );

  const env = captures.find((c) => c.environment)?.environment ?? {};
  const note = `ChatGPT capture v2 · ${env.interface ?? "chatgpt.com"} · model label ${env.modelSelectorLabel ?? "unknown"} · temporary chat, unpersonalized, web search on · one conversation per prompt · runId ${captures[0]?.runId}`;
  const batchIds: Record<string, string> = {};
  const batchFor = async (repeat: boolean) => {
    const name = repeat ? repeatName : benchName;
    if (!batchIds[name]) {
      const r = await pool.query(
        `INSERT INTO aio_batches (name, source_type, notes) VALUES ($1,$2,$3) RETURNING id`,
        [name, repeat ? REPEAT_SOURCE_TYPE : "manual_chatgpt", note],
      );
      batchIds[name] = r.rows[0].id;
    }
    return batchIds[name];
  };

  let imported = 0;
  let skipped = 0;
  for (const c of captures) {
    if (c.error || typeof c.answerText !== "string") {
      skipped += 1;
      console.warn(`skip ${c.key}: ${c.error ?? "no answer"}`);
      continue;
    }
    const sources = (c.sources ?? []).filter((s) => !isInterfaceUrl(s.url));
    const urls = [...new Set(sources.map((s) => s.url))];
    const evaluation = evaluateManualAudit({
      query: c.queryText,
      answer: c.answerText,
      proseText: c.proseText,
      citationUrls: urls,
      competitors: [...DEFAULT_COMPETITORS],
    });
    const capture = {
      schema: "aio_capture_v2",
      runId: c.runId,
      key: c.key,
      trial: c.trial,
      phase: c.phase,
      proseText: c.proseText ?? "",
      citationLabels: c.citationLabels ?? [],
      sources: sources.map((s) => ({
        url: s.url,
        title: s.title ?? null,
        publisher: s.publisher ?? null,
        paragraph: s.paragraph ?? null,
        hidden: !!s.hidden,
      })),
      citationStatus: c.citationStatus ?? "not_collected",
      environment: c.environment ?? null,
      conversationUrl: c.conversationUrl ?? null,
    };
    await pool.query(
      `INSERT INTO aio_manual_audits (
        batch_id, query_id, query_text, observed_at, product_note, raw_response, citations_json,
        clean_session_confirmed, notes, evaluation_json, evaluator_version, created_by, capture_json
      ) VALUES ($1,$2,$3,$4::timestamptz,$5,$6,$7::jsonb,$8,$9,$10::jsonb,$11,$12,$13::jsonb)`,
      [
        await batchFor(c.phase !== "benchmark"),
        knownIds.has(c.queryId) ? c.queryId : null,
        c.queryText,
        c.sentAt,
        "ChatGPT Search (consumer)",
        c.answerText,
        JSON.stringify(urls),
        true,
        `${c.key}${c.trial ? ` · trial ${c.trial}` : ""}`,
        JSON.stringify(evaluation),
        EVALUATOR_VERSION,
        "import-capture-v2",
        JSON.stringify(capture),
      ],
    );
    imported += 1;
  }
  console.log(JSON.stringify({ imported, skipped, batches: batchIds }, null, 1));
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
