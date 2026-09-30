/**
 * Rescores historical ChatGPT AIO captures with the visibility scorer, leaving the original
 * capture files and stored evaluations untouched. Output is a separately labeled corrected set.
 *
 *   npx tsx scripts/aio/rescore-history.ts
 *
 * Originals are read from the DB (aio_manual_audits.evaluation_json) when reachable.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

import {
  VISIBILITY_SCORER_VERSION,
  legacyCitationStatus,
  normalizeSourceUrl,
  scoreVisibility,
  stripCitationLabelsHeuristic,
} from "../../lib/aio/visibility-score";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.resolve(root, "../docs/marketing/aio/runs/2026-09-29");
const design = JSON.parse(fs.readFileSync(path.join(outDir, "benchmark_design.json"), "utf8"));
const informational = new Set<string>(design.queryClasses.informational);

type LegacyRecord = {
  queryId: string;
  queryText: string;
  rawResponse: string;
  citationUrls?: string[];
  capturedAt?: string;
};

const RUNS = [
  {
    runId: "2026-09-15",
    label: "Sep 15 baseline",
    file: "tmp/archive_2026-09-15_baseline/aio_audits_capture.jsonl",
    batchPrefix: "Baseline bulk - 2026-09-15",
    captureMethod:
      "Manual/assisted ChatGPT capture; answer innerText only. Citation URLs were not collected for any query.",
  },
  {
    runId: "2026-09-23",
    label: "Sep 23 full 46",
    file: "tmp/aio_full46_2026-09-23.jsonl",
    batchPrefix: "Full 46 - 2026-09-23",
    captureMethod:
      "Browser-assisted capture; answer innerText plus visible link hrefs. The first 9 queries have no URLs; hidden '+N' sources were never expanded.",
  },
  {
    runId: "2026-09-29-initial",
    label: "Sep 29 initial run",
    file: "tmp/aio_full46_2026-09-29.jsonl",
    batchPrefix: "Day-14 full 46 - 2026-09-29",
    captureMethod:
      "Browser-assisted capture (temporary chat, web search); answer innerText plus visible link hrefs. Hidden '+N' sources and citation titles were not collected.",
  },
];

function readJsonl(file: string): LegacyRecord[] {
  return fs
    .readFileSync(path.join(root, file), "utf8")
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

type Original = { mentioned: boolean | null; cited: boolean | null; evaluatorVersion: string | null };

async function loadOriginals(): Promise<Map<string, Map<string, Original>> | null> {
  const pool = new pg.Pool({
    connectionString:
      process.env.AUTH_DATABASE_URL ||
      process.env.DATABASE_URL ||
      "postgresql://sfi:sfi_dev_password@localhost:5432/sfi",
  });
  try {
    const { rows } = await pool.query(
      `select b.name batch, a.query_id, a.evaluator_version,
              a.evaluation_json->'smpl_mentioned' m, a.evaluation_json->'smpl_cited' c
         from aio_manual_audits a join aio_batches b on b.id = a.batch_id
        order by a.observed_at`,
    );
    const byRun = new Map<string, Map<string, Original>>();
    for (const run of RUNS) {
      const m = new Map<string, Original>();
      for (const r of rows) {
        if (!String(r.batch).startsWith(run.batchPrefix)) continue;
        m.set(r.query_id, { mentioned: r.m ?? null, cited: r.c ?? null, evaluatorVersion: r.evaluator_version });
      }
      byRun.set(run.runId, m);
    }
    return byRun;
  } catch (e) {
    console.warn("Originals unavailable (DB not reachable):", (e as Error).message);
    return null;
  } finally {
    await pool.end();
  }
}

async function main() {
  const originals = await loadOriginals();
  const output = {
    generatedAt: new Date().toISOString(),
    scorerVersion: VISIBILITY_SCORER_VERSION,
    note:
      "Corrected rescoring of stored answers only. No history was re-searched and no URLs were added; " +
      "citation status reports what the original capture could and could not show.",
    runs: [] as unknown[],
  };

  for (const run of RUNS) {
    const all = readJsonl(run.file);
    const byId = new Map<string, LegacyRecord>();
    const duplicates: string[] = [];
    for (const r of all) {
      if (byId.has(r.queryId)) duplicates.push(r.queryId);
      byId.set(r.queryId, r);
    }
    const rows = [...byId.values()].map((r) => {
      const urls = (r.citationUrls ?? []).filter(Boolean);
      const citationStatus = legacyCitationStatus(r.rawResponse, urls);
      const score = scoreVisibility({
        answerText: r.rawResponse,
        sources: urls.map((url) => ({ url })),
        citationStatus,
      });
      const orig = originals?.get(run.runId)?.get(r.queryId) ?? null;
      return {
        queryId: r.queryId,
        queryClass: informational.has(r.queryId) ? "informational" : "vendor_selection",
        capturedAt: r.capturedAt ?? null,
        original: orig,
        corrected: {
          proseMention: score.proseMention,
          recommendation: score.recommendation,
          vendorRecommended: score.vendorRecommended,
          recommendationEvidence: score.recommendationEvidence,
          smplCitation: score.smplCitation,
          smplCitationUrlVerified: score.smplCitationUrlVerified,
          smplCitationUrls: score.smplSources.map((s) => normalizeSourceUrl(s.url)),
          smplCitationLabels: score.smplCitationLabels,
          citationStatus,
          capturedSourceUrls: urls.length,
          citationLabelsInText: stripCitationLabelsHeuristic(r.rawResponse).labels.length,
          hiddenSourceMarkers: score.hiddenSourceMarkers,
          proseSnippets: score.proseSnippets,
        },
      };
    });
    const count = (f: (x: (typeof rows)[number]) => boolean) => rows.filter(f).length;
    const statusCounts: Record<string, number> = {};
    for (const r of rows)
      statusCounts[r.corrected.citationStatus] = (statusCounts[r.corrected.citationStatus] ?? 0) + 1;
    output.runs.push({
      runId: run.runId,
      label: run.label,
      sourceFile: run.file,
      captureMethod: run.captureMethod,
      modelRecorded: false,
      queries: rows.length,
      duplicateCapturesDropped: duplicates,
      original: originals
        ? {
            mentioned: count((r) => r.original?.mentioned === true),
            cited: count((r) => r.original?.cited === true),
            evaluatorVersions: [...new Set(rows.map((r) => r.original?.evaluatorVersion).filter(Boolean))],
          }
        : null,
      corrected: {
        proseMentions: count((r) => r.corrected.proseMention),
        vendorRecommendations: count((r) => r.corrected.vendorRecommended),
        recommendationLevels: rows
          .filter((r) => r.corrected.vendorRecommended)
          .map((r) => `${r.queryId}:${r.corrected.recommendation}`),
        smplCitations: count((r) => r.corrected.smplCitation === "yes"),
        smplCitationsUrlVerified: count((r) => r.corrected.smplCitationUrlVerified),
        citationStatus: statusCounts,
        smplCitationUnknownOrIncomplete: count(
          (r) => r.corrected.smplCitation === "unknown" || r.corrected.smplCitation === "not_in_visible_sources",
        ),
      },
      changedVsOriginal: rows
        .filter(
          (r) =>
            r.original &&
            (r.original.mentioned !== r.corrected.proseMention ||
              r.original.cited !== (r.corrected.smplCitation === "yes")),
        )
        .map((r) => ({
          queryId: r.queryId,
          original: { mentioned: r.original!.mentioned, cited: r.original!.cited },
          corrected: {
            proseMention: r.corrected.proseMention,
            recommendation: r.corrected.recommendation,
            smplCitation: r.corrected.smplCitation,
            smplCitationUrlVerified: r.corrected.smplCitationUrlVerified,
          },
        })),
      rows,
    });
  }

  const outFile = path.join(outDir, "corrected_history_visibility_v1.json");
  fs.writeFileSync(outFile, JSON.stringify(output, null, 2));
  for (const r of output.runs as any[]) {
    console.log(
      r.label,
      JSON.stringify({ original: r.original, corrected: r.corrected, changed: r.changedVsOriginal }),
    );
  }
  console.log("wrote", path.relative(process.cwd(), outFile));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
