/**
 * Local bulk import (no HTTP auth). Uses auth Postgres + rules_v1 evaluator.
 *
 *   npx --yes tsx scripts/aio-bulk-import-local.ts path/to/audits.jsonl
 */
import fs from "node:fs";
import path from "node:path";

import { createManualAudit, seedAioConfig } from "../lib/aio/db";

async function main() {
  const inputPath = process.argv[2];
  if (!inputPath) {
    console.error("Usage: npx tsx scripts/aio-bulk-import-local.ts <audits.json|jsonl>");
    process.exit(1);
  }
  const abs = path.resolve(inputPath);
  const raw = fs.readFileSync(abs, "utf8");
  let records: Array<Record<string, unknown>>;
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

  const batchName =
    process.env.AIO_BATCH_NAME ||
    `Baseline bulk - ${new Date().toISOString().slice(0, 10)}`;

  await seedAioConfig();
  let ok = 0;
  for (const [i, rec] of records.entries()) {
    const queryText = String(
      rec.queryText || rec.query_text || rec.query || "",
    ).trim();
    const rawResponse = String(
      rec.rawResponse || rec.raw_response || rec.answer || "",
    ).trim();
    if (!queryText || !rawResponse) {
      console.error(`[${i + 1}] skip: missing query/answer`);
      continue;
    }
    const citationUrls = Array.isArray(rec.citationUrls)
      ? (rec.citationUrls as string[])
      : Array.isArray(rec.citations)
        ? (rec.citations as string[])
        : [];
    const audit = await createManualAudit({
      queryId: (rec.queryId as string) || null,
      queryText,
      rawResponse,
      citationUrls,
      notes: String(rec.notes || ""),
      cleanSessionConfirmed: rec.cleanSessionConfirmed !== false,
      batchName: (rec.batchName as string) || batchName,
      productNote: String(rec.productNote || "ChatGPT Search (consumer)"),
      createdBy: "bulk-import-local",
    });
    ok += 1;
    const e = audit.evaluation_json;
    console.log(
      `[${i + 1}/${records.length}] ${rec.queryId || ""} mentioned=${e.smpl_mentioned} ${e.recommendation_strength} pos=${e.positioning_accuracy}`,
    );
  }
  console.log(`Imported ${ok}/${records.length} into batch "${batchName}"`);
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
