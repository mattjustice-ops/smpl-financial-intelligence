/**
 * Scores the Sep 29 controlled rerun (capture v2) and writes the comparison report.
 *
 *   npx tsx scripts/aio/rescore-history.ts      # corrected historical scores (run first)
 *   npx tsx scripts/aio/rerun-report.ts <rerun capture jsonl>
 *
 * Writes to docs/marketing/aio/runs/2026-09-29/:
 *   rerun_scored_visibility_v1.json, comparison_report.md, rerun_export_for_chatgpt.md
 * If conclusions.md exists in that folder it is appended to the report.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  VISIBILITY_SCORER_VERSION,
  type CitationStatus,
  type CitedSource,
  competitorForUrl,
  domainSummary,
  isInterfaceUrl,
  normalizeSourceUrl,
  scoreVisibility,
  sourceDomain,
  stripCitationLabelsHeuristic,
  vendorsMentioned,
} from "../../lib/aio/visibility-score";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.resolve(root, "../docs/marketing/aio/runs/2026-09-29");
const input = process.argv[2];
if (!input) {
  console.error("Usage: npx tsx scripts/aio/rerun-report.ts <rerun capture jsonl>");
  process.exit(1);
}

type Pill = { label: string; publisher: string | null; title: string | null; url: string; additionalCount: number };
type Capture = {
  key: string;
  queryId: string;
  queryText: string;
  trial: number | null;
  phase: string;
  promptMatches?: boolean;
  conversationUrl?: string;
  sentAt?: string;
  completedAt?: string;
  durationSec?: number;
  responseTimedOut?: boolean;
  environment?: Record<string, unknown>;
  answerText?: string;
  proseText?: string;
  citationLabels?: string[];
  pills?: Pill[];
  sources?: Array<CitedSource & { pillIndex: number | null; inline?: boolean }>;
  citationStatus?: CitationStatus;
  expansionFailures?: number;
  error?: string;
};

const design = JSON.parse(fs.readFileSync(path.join(outDir, "benchmark_design.json"), "utf8"));
const informational = new Set<string>(design.queryClasses.informational);
const priority: string[] = design.priorityQueries.map((p: { id: string } | string) => (typeof p === "string" ? p : p.id));
const history = JSON.parse(fs.readFileSync(path.join(outDir, "corrected_history_visibility_v1.json"), "utf8"));
const histRun = (id: string) => history.runs.find((r: { runId: string }) => r.runId === id);
const initial = histRun("2026-09-29-initial");

const captures: Capture[] = fs
  .readFileSync(path.resolve(input), "utf8")
  .split(/\r?\n/)
  .filter((l) => l.trim())
  .map((l) => JSON.parse(l));

const scored = captures.map((c) => {
  if (c.error || typeof c.answerText !== "string") return { capture: c, score: null, heuristic: null, vendors: [] };
  const sources = (c.sources ?? []).filter((s) => !isInterfaceUrl(s.url));
  const score = scoreVisibility({
    answerText: c.answerText,
    proseText: c.proseText ?? null,
    sources,
    citationLabels: c.citationLabels ?? [],
    citationStatus: c.citationStatus ?? "not_collected",
  });
  // Legacy path on the same answer: innerText only, visible URLs only, label-strip heuristic.
  const visibleUrls = sources.filter((s) => !s.hidden).map((s) => s.url);
  const heuristic = scoreVisibility({
    answerText: c.answerText,
    sources: visibleUrls.map((url) => ({ url })),
    citationStatus: visibleUrls.length ? "partial" : "labels_only",
  });
  const labelStrip = stripCitationLabelsHeuristic(c.answerText);
  return {
    capture: c,
    score,
    heuristic: { ...heuristic, labelCount: labelStrip.labels.length, pillCount: (c.pills ?? []).length },
    vendors: vendorsMentioned(c.proseText ?? c.answerText),
  };
});
type Scored = (typeof scored)[number];

const bench = scored.filter((s) => s.capture.phase === "benchmark");
const trialsFor = (id: string) =>
  scored
    .filter((s) => s.capture.queryId === id && (s.capture.phase === "priority_repeat" || s.capture.phase === "benchmark"))
    .sort((a, b) => (a.capture.trial ?? 1) - (b.capture.trial ?? 1));

const yes = (b: boolean) => (b ? "yes" : "—");
const cls = (id: string) => (informational.has(id) ? "informational" : "vendor_selection");
const counts = (rows: Scored[]) => ({
  n: rows.length,
  captured: rows.filter((r) => r.score).length,
  prose: rows.filter((r) => r.score?.proseMention).length,
  rec: rows.filter((r) => r.score?.vendorRecommended).length,
  cite: rows.filter((r) => r.score?.smplCitation === "yes").length,
});
const citeState = (s: Scored) => (s.score ? s.score.smplCitation : "no capture");
const visStr = (r: { proseMention: boolean; recommendation: string; smplCitation: string } | null) =>
  !r ? "no capture" : `prose ${yes(r.proseMention)} · rec ${r.recommendation} · cite ${r.smplCitation}`;

const md: string[] = [];
const L = (s = "") => md.push(s);

L("# SMPL.ai ChatGPT AIO benchmark — Sep 29, 2026 audit and controlled rerun");
L();
L(`Generated ${new Date().toISOString()} · scorer \`${VISIBILITY_SCORER_VERSION}\` · rerun capture \`${path.basename(input)}\``);
L();
L("Three outcomes are scored separately:");
L("- **Prose mention**: SMPL.ai named in the answer's own text (citation-pill labels excluded).");
L("- **Vendor recommendation**: SMPL.ai presented as a product (listed < shortlisted < recommended < top pick).");
L("- **Source citation**: a SMPL.ai page is shown as a source. `unknown` / `not_in_visible_sources` mean the capture could not show every source, not that SMPL was absent.");
L();

// Conditions
const envs = scored.map((s) => s.capture.environment).filter(Boolean) as Record<string, unknown>[];
const uniq = (k: string) => [...new Set(envs.map((e) => String(e[k])))].join(", ");
const firstSent = scored.map((s) => s.capture.sentAt).filter(Boolean).sort()[0];
const lastDone = scored.map((s) => s.capture.completedAt).filter(Boolean).sort().slice(-1)[0];
const convs = new Set(scored.map((s) => s.capture.conversationUrl).filter(Boolean));
L("## 1. Rerun conditions");
L();
L(`- Interface: ${uniq("interface")}`);
const modelLabels: Record<string, number> = {};
for (const e of envs) {
  const k = e.modelSelectorLabel ? String(e.modelSelectorLabel) : "not rendered at send time";
  modelLabels[k] = (modelLabels[k] ?? 0) + 1;
}
L(`- Model selector label: ${Object.entries(modelLabels).map(([k, v]) => `${k} (${v})`).join(", ")}; the underlying model version is not exposed by the UI`);
L(`- Search: web search selected on every prompt: ${envs.every((e) => e.webSearchSelected) ? "yes" : "NO"}`);
L(`- Session: temporary chat on every prompt: ${envs.every((e) => e.temporaryChat) ? "yes" : "NO"}; personalization: ${uniq("personalization")}; "ignores memory, plugins, and custom instructions" notice shown: ${envs.every((e) => e.memoryAndInstructionsIgnoredNotice) ? "yes" : "NO"}`);
L(`- Independent conversations: ${convs.size} distinct conversation URLs for ${scored.filter((s) => s.score).length} answered prompts`);
L(`- Prompts sent verbatim: ${scored.every((s) => s.capture.promptMatches !== false) ? "yes (composer text matched the benchmark text before every send)" : "NO — see capture file"}`);
L(`- Time window: ${firstSent} → ${lastDone} (UTC); viewport ${uniq("viewport")}`);
L(`- Captures with errors: ${scored.filter((s) => !s.score).map((s) => `${s.capture.key} (${s.capture.error})`).join(", ") || "none"}`);
L();

// Historical original vs corrected
L("## 2. Historical results: original vs corrected");
L();
L("| Run | Original: mentioned | Original: cited | Corrected: prose mention | Corrected: recommendation | Corrected: SMPL citation (URL verified) | Citation capture status |");
L("|---|---|---|---|---|---|---|");
for (const r of history.runs) {
  const st = Object.entries(r.corrected.citationStatus).map(([k, v]) => `${k} ${v}`).join(", ");
  L(`| ${r.label} | ${r.original?.mentioned ?? "?"} | ${r.original?.cited ?? "?"} | ${r.corrected.proseMentions} | ${r.corrected.vendorRecommendations} (${r.corrected.recommendationLevels.join(", ") || "none"}) | ${r.corrected.smplCitations} (${r.corrected.smplCitationsUrlVerified}) | ${st} |`);
}
L();
L("Changes from the original reports:");
for (const r of history.runs) {
  if (!r.changedVsOriginal.length) L(`- ${r.label}: no change to mention/citation counts.`);
  for (const c of r.changedVsOriginal) {
    L(`- ${r.label} · ${c.queryId}: originally mentioned=${c.original.mentioned}, cited=${c.original.cited} → prose mention ${c.corrected.proseMention}, recommendation ${c.corrected.recommendation}, citation ${c.corrected.smplCitation}${c.corrected.smplCitation === "yes" && !c.corrected.smplCitationUrlVerified ? " (label only; URL never captured)" : ""}.`);
  }
}
L();

// Today initial vs rerun
const bc = counts(bench);
const bInfo = counts(bench.filter((b) => informational.has(b.capture.queryId)));
const bVend = counts(bench.filter((b) => !informational.has(b.capture.queryId)));
const iRows = initial.rows as Array<{ queryId: string; queryClass: string; corrected: { proseMention: boolean; vendorRecommended: boolean; recommendation: string; smplCitation: string } }>;
const iCount = (f: (r: (typeof iRows)[number]) => boolean) => iRows.filter(f).length;
L("## 3. Sep 29: initial run vs controlled rerun (46 prompts)");
L();
L("| | Prose mentions | Recommendations | SMPL citations | Citation status |");
L("|---|---|---|---|---|");
L(`| Initial run (corrected) | ${initial.corrected.proseMentions} | ${initial.corrected.vendorRecommendations} | ${initial.corrected.smplCitations} | ${Object.entries(initial.corrected.citationStatus).map(([k, v]) => `${k} ${v}`).join(", ")} |`);
const rStatus: Record<string, number> = {};
for (const b of bench) rStatus[b.score?.citationStatus ?? "no capture"] = (rStatus[b.score?.citationStatus ?? "no capture"] ?? 0) + 1;
L(`| Controlled rerun | ${bc.prose} | ${bc.rec} | ${bc.cite} | ${Object.entries(rStatus).map(([k, v]) => `${k} ${v}`).join(", ")} |`);
L();
L("By query class (rerun / initial):");
L();
L("| Class | Queries | Prose mentions | Recommendations | SMPL citations |");
L("|---|---|---|---|---|");
for (const [name, c, klass] of [["Informational", bInfo, "informational"], ["Vendor selection", bVend, "vendor_selection"]] as const) {
  L(`| ${name} | ${c.n} | ${c.prose} / ${iCount((r) => r.queryClass === klass && r.corrected.proseMention)} | ${c.rec} / ${iCount((r) => r.queryClass === klass && r.corrected.vendorRecommended)} | ${c.cite} / ${iCount((r) => r.queryClass === klass && r.corrected.smplCitation === "yes")} |`);
}
L();

// Query-level gains / losses
const runsForGrid = history.runs.map((r: { label: string; rows: unknown[] }) => ({ label: r.label, rows: r.rows as typeof iRows }));
const anyVis = (c: { proseMention: boolean; vendorRecommended?: boolean; smplCitation: string } | null | undefined) =>
  !!c && (c.proseMention || !!c.vendorRecommended || c.smplCitation === "yes");
const touched = new Set<string>();
for (const r of runsForGrid) for (const row of r.rows) if (anyVis(row.corrected)) touched.add(row.queryId);
for (const s of scored) if (anyVis(s.score)) touched.add(s.capture.queryId);
L("## 4. Query-level SMPL appearances across runs");
L();
L("Every query where SMPL.ai appeared in any run, by any of the three outcomes. All other queries: no appearance in any run.");
L();
L(`| Query | Class | ${runsForGrid.map((r: { label: string }) => r.label).join(" | ")} | Rerun (trial 1) | Priority trial 2 | Priority trial 3 |`);
L(`|---|---|${runsForGrid.map(() => "---").join("|")}|---|---|---|`);
for (const id of [...touched].sort()) {
  const hist = runsForGrid.map((r: { rows: typeof iRows }) => {
    const row = r.rows.find((x) => x.queryId === id);
    return row ? visStr(row.corrected) : "not run";
  });
  const t = [1, 2, 3].map((n) => {
    const s = scored.find((x) => x.capture.queryId === id && (x.capture.trial ?? (x.capture.phase === "benchmark" ? 1 : 0)) === n);
    return s ? visStr(s.score) : "—";
  });
  L(`| ${id} | ${cls(id)} | ${hist.join(" | ")} | ${t.join(" | ")} |`);
}
L();
const gained = bench.filter((b) => anyVis(b.score) && !anyVis(iRows.find((r) => r.queryId === b.capture.queryId)?.corrected)).map((b) => b.capture.queryId);
const lost = iRows.filter((r) => anyVis(r.corrected) && !anyVis(bench.find((b) => b.capture.queryId === r.queryId)?.score)).map((r) => r.queryId);
L(`Initial → rerun, same day: gained ${gained.join(", ") || "none"}; lost ${lost.join(", ") || "none"}.`);
L();

// Priority frequency
L("## 5. Priority queries: appearance frequency across 3 trials");
L();
L("Priority set fixed in `benchmark_design.json` before any rerun result was seen. Trial 1 is the query's response inside the controlled 46-prompt rerun; trials 2–3 are repeats under identical conditions. The earlier Sep 29 run used a different capture method and is shown separately, not counted as a trial.");
L();
L("| Query | Class | Prose mention (of 3) | Recommended (of 3) | SMPL cited (of 3) | Cited-domain overlap across trials | Vendor-list overlap across trials | Sep 29 initial (not a trial) |");
L("|---|---|---|---|---|---|---|---|");
const jaccard = (sets: Set<string>[]) => {
  if (sets.length < 2) return null;
  const inter = sets.reduce((a, b) => new Set([...a].filter((x) => b.has(x))));
  const union = new Set(sets.flatMap((s) => [...s]));
  return union.size ? inter.size / union.size : 1;
};
const domainsOf = (s: Scored) =>
  new Set((s.capture.sources ?? []).filter((x) => !isInterfaceUrl(x.url)).map((x) => sourceDomain(x.url)!).filter(Boolean));
const stability: Array<{ id: string; dom: number | null; ven: number | null }> = [];
for (const id of priority) {
  const tr = trialsFor(id).filter((t) => t.score);
  const n = tr.length;
  const dom = jaccard(tr.map(domainsOf));
  const ven = jaccard(tr.map((t) => new Set(t.vendors)));
  stability.push({ id, dom, ven });
  const pct = (x: number | null) => (x == null ? "n/a" : `${Math.round(x * 100)}%`);
  const ini = iRows.find((r) => r.queryId === id);
  L(`| ${id} | ${cls(id)} | ${tr.filter((t) => t.score!.proseMention).length}/${n} | ${tr.filter((t) => t.score!.vendorRecommended).length}/${n} | ${tr.filter((t) => t.score!.smplCitation === "yes").length}/${n} | ${pct(dom)} | ${pct(ven)} | ${ini ? visStr(ini.corrected) : "—"} |`);
}
L();
L("Overlap = items present in all trials ÷ items present in any trial (Jaccard). Low overlap means the same prompt produced materially different sources or vendor lists within hours.");
L();

// Citation completeness
const all = scored.filter((s) => s.score);
const hiddenTotal = all.reduce((a, s) => a + (s.capture.sources ?? []).filter((x) => x.hidden).length, 0);
const srcTotal = all.reduce((a, s) => a + (s.capture.sources ?? []).length, 0);
const agreeProse = all.filter((s) => s.heuristic!.proseMention === s.score!.proseMention).length;
const agreeRec = all.filter((s) => s.heuristic!.recommendation === s.score!.recommendation).length;
const agreeLabels = all.filter((s) => s.heuristic!.labelCount === s.heuristic!.pillCount).length;
L("## 6. Citation capture completeness and comparability");
L();
L(`- Rerun: ${all.length} answers, ${srcTotal} source entries, of which ${hiddenTotal} (${Math.round((100 * hiddenTotal) / Math.max(1, srcTotal))}%) were hidden behind "+N" pills. Earlier captures never collected those, so their citation results are lower bounds.`);
const visibleOnlyCites = bench.filter(
  (b) => b.score?.smplCitation === "yes" && b.score.smplSources.some((s) => !s.hidden),
).length;
L(`- Like-for-like with earlier runs (visible sources only, as their capture saw them): ${visibleOnlyCites} of ${bc.cite} rerun SMPL citations would have been detected; the rest appeared only behind "+N" pills.`);
L(`- Rerun citation status: ${Object.entries(all.reduce((a: Record<string, number>, s) => ((a[s.score!.citationStatus] = (a[s.score!.citationStatus] ?? 0) + 1), a), {})).map(([k, v]) => `${k} ${v}`).join(", ")}.`);
L(`- Historical label-strip heuristic vs structural capture on the same rerun answers: prose-mention agreement ${agreeProse}/${all.length}; recommendation-level agreement ${agreeRec}/${all.length}; pill-label count exact match ${agreeLabels}/${all.length}.`);
L("- Model version was not recorded for Sep 15, Sep 23, or the Sep 29 initial run; the rerun records only the UI selector label. Sep 15 citation URLs were never collected; Sep 23's first 9 queries have no URLs.");
L();

// Domain reconciliation + competitor URLs
const benchSources = bench.filter((b) => b.score).map((b) => ({ sources: (b.capture.sources ?? []) as CitedSource[] }));
const ds = domainSummary(benchSources);
const perQueryDomainTotal = benchSources.reduce((a, r) => {
  const d = new Set(r.sources.filter((s) => !isInterfaceUrl(s.url)).map((s) => sourceDomain(s.url)));
  return a + d.size;
}, 0);
const summaryTotal = ds.reduce((a, r) => a + r.answers, 0);
L("## 7. Cited domains (controlled rerun, 46 prompts)");
L();
L(`Reconciliation: the domain table is built from the same per-answer source lists printed in the export. Sum of per-answer distinct domains = ${perQueryDomainTotal}; sum of the table's "answers" column = ${summaryTotal} → ${perQueryDomainTotal === summaryTotal ? "reconciled" : "MISMATCH"}.`);
L();
L("| Domain | Answers citing | Distinct pages |");
L("|---|---|---|");
for (const r of ds.slice(0, 20)) L(`| ${r.domain} | ${r.answers} | ${r.sources} |`);
L();
const compUrls = new Map<string, { vendor: string; answers: Set<string>; title: string | null }>();
for (const s of scored.filter((x) => x.score)) {
  for (const src of s.capture.sources ?? []) {
    const vendor = competitorForUrl(src.url);
    const u = normalizeSourceUrl(src.url);
    if (!vendor || !u) continue;
    const row = compUrls.get(u) ?? { vendor, answers: new Set<string>(), title: src.title ?? null };
    row.answers.add(s.capture.key);
    compUrls.set(u, row);
  }
}
L("### Most-cited competitor URLs (all 66 rerun answers)");
L();
L("| Vendor | URL | Answers citing | Title |");
L("|---|---|---|---|");
for (const [u, r] of [...compUrls.entries()].sort((a, b) => b[1].answers.size - a[1].answers.size).slice(0, 15)) {
  L(`| ${r.vendor} | ${u} | ${r.answers.size} | ${(r.title ?? "").replace(/\|/g, "/").slice(0, 80)} |`);
}
L();
const vendorCounts = new Map<string, number>();
for (const b of bench.filter((x) => x.score)) for (const v of b.vendors) vendorCounts.set(v, (vendorCounts.get(v) ?? 0) + 1);
L(`Vendors named in prose across the 46 rerun answers: ${[...vendorCounts.entries()].sort((a, b) => b[1] - a[1]).map(([v, n]) => `${v} ${n}`).join(", ")}; SMPL.ai ${bc.prose}.`);
L();

const conclusions = path.join(outDir, "conclusions.md");
if (fs.existsSync(conclusions)) {
  L(fs.readFileSync(conclusions, "utf8").trim());
  L();
}
fs.writeFileSync(path.join(outDir, "comparison_report.md"), md.join("\n"));

// Machine-readable scored rerun
fs.writeFileSync(
  path.join(outDir, "rerun_scored_visibility_v1.json"),
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      scorerVersion: VISIBILITY_SCORER_VERSION,
      sourceFile: path.basename(input),
      stability,
      rows: scored.map((s) => ({
        key: s.capture.key,
        queryId: s.capture.queryId,
        queryClass: cls(s.capture.queryId),
        phase: s.capture.phase,
        trial: s.capture.trial,
        sentAt: s.capture.sentAt,
        conversationUrl: s.capture.conversationUrl,
        environment: s.capture.environment,
        error: s.capture.error ?? null,
        citationStatus: s.score?.citationStatus ?? null,
        score: s.score,
        heuristicScore: s.heuristic && {
          proseMention: s.heuristic.proseMention,
          recommendation: s.heuristic.recommendation,
          labelCount: s.heuristic.labelCount,
          pillCount: s.heuristic.pillCount,
        },
        vendorsInProse: s.vendors,
        sources: (s.capture.sources ?? [])
          .filter((x) => !isInterfaceUrl(x.url))
          .map((x) => ({ url: normalizeSourceUrl(x.url), title: x.title, publisher: x.publisher, hidden: !!x.hidden })),
      })),
    },
    null,
    2,
  ),
);

// Export with working source links
const ex: string[] = [];
ex.push("# SMPL.ai ChatGPT AIO — Sep 29, 2026 controlled rerun (export)");
ex.push("");
ex.push(`Scorer ${VISIBILITY_SCORER_VERSION}. Interface: ${uniq("interface")}; model label: ${uniq("modelSelectorLabel")}; temporary chat, unpersonalized, web search on; one conversation per prompt. Source URLs have utm parameters removed. "(hidden)" marks sources shown only behind a "+N" pill.`);
ex.push("");
for (const s of scored) {
  const c = s.capture;
  ex.push(`## ${c.key} — ${c.queryText}`);
  ex.push("");
  ex.push(`- Class: ${cls(c.queryId)} · phase ${c.phase}${c.trial ? ` · trial ${c.trial}` : ""} · sent ${c.sentAt ?? "?"}`);
  if (!s.score) {
    ex.push(`- Capture error: ${c.error}`);
    ex.push("");
    continue;
  }
  ex.push(`- SMPL prose mention: ${s.score.proseMention ? "yes" : "no"} · recommendation: ${s.score.recommendation} · SMPL citation: ${citeState(s)} · citation status: ${s.score.citationStatus}`);
  if (s.score.recommendationEvidence) ex.push(`- Recommendation evidence: "${s.score.recommendationEvidence}"`);
  ex.push(`- Vendors named: ${s.vendors.join(", ") || "none"}`);
  ex.push("");
  ex.push("### Answer (citation labels removed)");
  ex.push("");
  ex.push((c.proseText ?? c.answerText ?? "").trim());
  ex.push("");
  ex.push("### Sources");
  ex.push("");
  const seen = new Set<string>();
  for (const src of c.sources ?? []) {
    const u = normalizeSourceUrl(src.url);
    if (!u || isInterfaceUrl(src.url) || seen.has(u)) continue;
    seen.add(u);
    ex.push(`- [${(src.title || src.publisher || u).replace(/[[\]]/g, "")}](${u})${src.publisher ? ` — ${src.publisher}` : ""}${src.hidden ? " (hidden)" : ""}`);
  }
  if (!seen.size) ex.push("- none shown");
  ex.push("");
}
fs.writeFileSync(path.join(outDir, "rerun_export_for_chatgpt.md"), ex.join("\n"));

console.log(JSON.stringify({ bench: bc, info: bInfo, vendor: bVend, gained, lost, stability }, null, 1));
