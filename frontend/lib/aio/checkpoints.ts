/**
 * Groups stored ChatGPT audits into benchmark checkpoints (one full run of the query bank)
 * and scores each answer with the visibility scorer. Headline outcomes (named as a product,
 * shortlisted or better) come from the answer text only; citations, prose mentions, and
 * hidden "+N" sources are diagnostics. Pure: callers supply the rows.
 */
import {
  type CitationStatus,
  type CitationVisibility,
  type CitedSource,
  type RecommendationLevel,
  legacyCitationStatus,
  normalizeSourceUrl,
  scoreVisibility,
} from "@/lib/aio/visibility-score";

export type CaptureV2Json = {
  schema: "aio_capture_v2";
  runId: string;
  key: string;
  trial: number | null;
  phase: string;
  proseText: string;
  citationLabels: string[];
  sources: CitedSource[];
  citationStatus: CitationStatus;
  environment?: Record<string, unknown>;
  conversationUrl?: string;
};

export type CheckpointAuditRow = {
  batch_name: string | null;
  batch_source_type: string | null;
  query_id: string | null;
  query_text?: string | null;
  observed_at: string | Date;
  raw_response: string;
  citations_json: unknown;
  capture_json: CaptureV2Json | null;
  evaluation_json: { smpl_mentioned?: boolean; smpl_cited?: boolean } | null;
};

export type QueryClass = "informational" | "vendor_selection";

/** Per-answer outcomes, headline first. */
export type AnswerOutcome = {
  /** Listed, shortlisted, recommended, or top pick as a vendor option. */
  namedAsProduct: boolean;
  shortlistPlus: boolean;
  recommendation: RecommendationLevel;
  /** Any SMPL mention in the answer text, including passing references ("according to SMPL.ai"). */
  mentioned: boolean;
  citation: CitationVisibility;
};

export type ScoredAnswer = AnswerOutcome & {
  queryId: string;
  cited: boolean;
  citedUrlVerified: boolean;
  citationStatus: CitationStatus;
  smplPages: string[];
  hiddenSmplPages: string[];
  structural: boolean;
};

export type OutcomeCounts = {
  queries: number;
  namedAsProduct: number;
  shortlistPlus: number;
  mentioned: number;
  cited: number;
  visibleCited: number;
  hiddenOnlyCited: number;
  citedVisibilityUnknown: number;
};

export type CheckpointSummary = OutcomeCounts & {
  key: string;
  label: string;
  startedAt: string;
  method: "capture_v2" | "legacy" | "mixed";
  runId: string | null;
  /** False when any answer came from an older capture that never collected hidden "+N" sources. */
  citationVisibilityKnown: boolean;
  citedUrlVerified: number;
  citationComplete: number;
  citationIsLowerBound: boolean;
  citationStatus: Record<string, number>;
  originalMentioned: number;
  originalCited: number;
  byClass: Record<QueryClass, OutcomeCounts>;
  smplPages: Array<{ url: string; answers: number; hiddenOnlyAnswers: number }>;
};

export type TrialCell = AnswerOutcome & { trial: number };

export type PriorityFrequency = {
  checkpointKey: string;
  checkpointLabel: string;
  queries: Array<{
    queryId: string;
    queryText: string;
    queryClass: QueryClass;
    trials: TrialCell[];
    namedAsProduct: number;
    shortlistPlus: number;
    mentioned: number;
    visibleCited: number;
    hiddenOnlyCited: number;
  }>;
};

export type VisibilityHistory = {
  checkpoints: CheckpointSummary[];
  appearanceGrid: Array<{
    queryId: string;
    queryText: string;
    queryClass: QueryClass;
    cells: Array<AnswerOutcome | null>;
  }>;
  priority: PriorityFrequency | null;
};

/** Batches of repeat trials; excluded from "latest answer per query" views. */
export const REPEAT_SOURCE_TYPE = "manual_chatgpt_repeat";
/** A batch group counts as a full benchmark checkpoint once it covers this many distinct queries. */
export const MIN_CHECKPOINT_QUERIES = 30;

const SHORTLIST_PLUS: RecommendationLevel[] = ["shortlisted", "recommended", "top_pick"];

/** Batches continued across sessions ("… (cont)") belong to the same checkpoint. */
export function checkpointName(batchName: string | null): string {
  return (batchName || "Unbatched").replace(/\s*\(cont\)\s*$/i, "").trim();
}

function asUrls(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && !!x) : [];
}

export function scoreAuditRow(row: CheckpointAuditRow): ScoredAnswer {
  const cap = row.capture_json?.schema === "aio_capture_v2" ? row.capture_json : null;
  const urls = asUrls(row.citations_json);
  const citationStatus = cap ? cap.citationStatus : legacyCitationStatus(row.raw_response, urls);
  const s = scoreVisibility(
    cap
      ? {
          answerText: row.raw_response,
          proseText: cap.proseText,
          sources: cap.sources,
          citationLabels: cap.citationLabels,
          citationStatus,
        }
      : { answerText: row.raw_response, sources: urls.map((url) => ({ url })), citationStatus },
  );
  const pages = (hidden: boolean) => [
    ...new Set(
      s.smplSources
        .filter((x) => !!x.hidden === hidden)
        .map((x) => normalizeSourceUrl(x.url))
        .filter((u): u is string => !!u),
    ),
  ];
  const visiblePages = pages(false);
  const hiddenPages = pages(true);
  return {
    queryId: row.query_id || "",
    namedAsProduct: s.vendorRecommended,
    shortlistPlus: SHORTLIST_PLUS.includes(s.recommendation),
    recommendation: s.recommendation,
    mentioned: s.proseMention,
    citation: s.smplCitationVisibility,
    cited: s.smplCitation === "yes",
    citedUrlVerified: s.smplCitationUrlVerified,
    citationStatus,
    smplPages: [...new Set([...visiblePages, ...hiddenPages])],
    hiddenSmplPages: hiddenPages.filter((u) => !visiblePages.includes(u)),
    structural: !!cap,
  };
}

function outcomeOf(a: ScoredAnswer): AnswerOutcome {
  return {
    namedAsProduct: a.namedAsProduct,
    shortlistPlus: a.shortlistPlus,
    recommendation: a.recommendation,
    mentioned: a.mentioned,
    citation: a.citation,
  };
}

const time = (v: string | Date) => new Date(v).getTime();

function emptyCounts(): OutcomeCounts {
  return {
    queries: 0,
    namedAsProduct: 0,
    shortlistPlus: 0,
    mentioned: 0,
    cited: 0,
    visibleCited: 0,
    hiddenOnlyCited: 0,
    citedVisibilityUnknown: 0,
  };
}

function addCounts(c: OutcomeCounts, a: ScoredAnswer) {
  c.queries += 1;
  if (a.namedAsProduct) c.namedAsProduct += 1;
  if (a.shortlistPlus) c.shortlistPlus += 1;
  if (a.mentioned) c.mentioned += 1;
  if (a.cited) c.cited += 1;
  if (a.citation === "visible") c.visibleCited += 1;
  if (a.citation === "hidden_only") c.hiddenOnlyCited += 1;
  if (a.citation === "unknown") c.citedVisibilityUnknown += 1;
}

/**
 * Full benchmark checkpoints (repeat batches excluded), oldest first, each holding the latest
 * answer per query.
 */
export function groupCheckpoints<T extends CheckpointAuditRow>(
  rows: T[],
): Array<{ name: string; startedAt: number; latest: Map<string, T> }> {
  const groups = new Map<string, Map<string, T>>();
  for (const r of rows) {
    if (!r.query_id || r.batch_source_type === REPEAT_SOURCE_TYPE) continue;
    const name = checkpointName(r.batch_name);
    const latest = groups.get(name) ?? new Map<string, T>();
    const prev = latest.get(r.query_id);
    if (!prev || time(r.observed_at) >= time(prev.observed_at)) latest.set(r.query_id, r);
    groups.set(name, latest);
  }
  return [...groups.entries()]
    .filter(([, latest]) => latest.size >= MIN_CHECKPOINT_QUERIES)
    .map(([name, latest]) => ({
      name,
      latest,
      startedAt: Math.min(...[...latest.values()].map((r) => time(r.observed_at))),
    }))
    .sort((a, b) => a.startedAt - b.startedAt);
}

export function buildVisibilityHistory(rows: CheckpointAuditRow[], informationalIds: Iterable<string>): VisibilityHistory {
  const informational = new Set(informationalIds);
  const classOf = (id: string): QueryClass => (informational.has(id) ? "informational" : "vendor_selection");
  const repeats = rows.filter((r) => r.query_id && r.batch_source_type === REPEAT_SOURCE_TYPE);
  const textOf = new Map<string, string>();
  for (const r of rows) if (r.query_id && r.query_text) textOf.set(r.query_id, r.query_text);

  type Built = { summary: CheckpointSummary; byQuery: Map<string, ScoredAnswer> };
  const built: Built[] = [];
  for (const { name, latest, startedAt } of groupCheckpoints(rows)) {
    const byQuery = new Map<string, ScoredAnswer>();
    const byClass: Record<QueryClass, OutcomeCounts> = { informational: emptyCounts(), vendor_selection: emptyCounts() };
    const total = emptyCounts();
    const status: Record<string, number> = {};
    const pages = new Map<string, { answers: number; hiddenOnlyAnswers: number }>();
    let verified = 0;
    let complete = 0;
    let structural = 0;
    let origM = 0;
    let origC = 0;
    let runId: string | null = null;
    for (const [qid, r] of latest) {
      const a = scoreAuditRow(r);
      byQuery.set(qid, a);
      addCounts(total, a);
      addCounts(byClass[classOf(qid)], a);
      status[a.citationStatus] = (status[a.citationStatus] ?? 0) + 1;
      if (a.citedUrlVerified) verified += 1;
      if (a.citationStatus === "complete" || a.citationStatus === "none_shown") complete += 1;
      if (a.structural) structural += 1;
      for (const p of a.smplPages) {
        const e = pages.get(p) ?? { answers: 0, hiddenOnlyAnswers: 0 };
        e.answers += 1;
        if (a.hiddenSmplPages.includes(p)) e.hiddenOnlyAnswers += 1;
        pages.set(p, e);
      }
      if (r.evaluation_json?.smpl_mentioned) origM += 1;
      if (r.evaluation_json?.smpl_cited) origC += 1;
      runId ??= r.capture_json?.runId ?? null;
    }
    built.push({
      byQuery,
      summary: {
        key: name,
        label: name,
        startedAt: new Date(startedAt).toISOString(),
        method: structural === latest.size ? "capture_v2" : structural === 0 ? "legacy" : "mixed",
        runId,
        ...total,
        citationVisibilityKnown: structural === latest.size,
        citedUrlVerified: verified,
        citationComplete: complete,
        citationIsLowerBound: complete < latest.size,
        citationStatus: status,
        originalMentioned: origM,
        originalCited: origC,
        byClass,
        smplPages: [...pages.entries()].map(([url, e]) => ({ url, ...e })).sort((a, b) => b.answers - a.answers),
      },
    });
  }

  const touched = new Set<string>();
  for (const b of built) for (const [qid, a] of b.byQuery) if (a.mentioned || a.namedAsProduct || a.cited) touched.add(qid);
  const appearanceGrid = [...touched].sort().map((queryId) => ({
    queryId,
    queryText: textOf.get(queryId) ?? "",
    queryClass: classOf(queryId),
    cells: built.map((b) => {
      const a = b.byQuery.get(queryId);
      return a ? outcomeOf(a) : null;
    }),
  }));

  // Repeat trials pair with the checkpoint captured in the same run; report the latest such run.
  let priority: PriorityFrequency | null = null;
  const repeatRunIds = [...new Set(repeats.map((r) => r.capture_json?.runId).filter((x): x is string => !!x))];
  for (const b of [...built].reverse()) {
    if (!b.summary.runId || !repeatRunIds.includes(b.summary.runId)) continue;
    const runRepeats = repeats.filter((r) => r.capture_json?.runId === b.summary.runId);
    const ids = [...new Set(runRepeats.map((r) => r.query_id!))];
    priority = {
      checkpointKey: b.summary.key,
      checkpointLabel: b.summary.label,
      queries: ids.map((queryId) => {
        const trials: TrialCell[] = [];
        const first = b.byQuery.get(queryId);
        if (first) trials.push({ trial: 1, ...outcomeOf(first) });
        for (const r of runRepeats.filter((x) => x.query_id === queryId)) {
          trials.push({ trial: r.capture_json?.trial ?? trials.length + 1, ...outcomeOf(scoreAuditRow(r)) });
        }
        trials.sort((x, y) => x.trial - y.trial);
        return {
          queryId,
          queryText: textOf.get(queryId) ?? "",
          queryClass: classOf(queryId),
          trials,
          namedAsProduct: trials.filter((t) => t.namedAsProduct).length,
          shortlistPlus: trials.filter((t) => t.shortlistPlus).length,
          mentioned: trials.filter((t) => t.mentioned).length,
          visibleCited: trials.filter((t) => t.citation === "visible").length,
          hiddenOnlyCited: trials.filter((t) => t.citation === "hidden_only").length,
        };
      }),
    };
    break;
  }

  return { checkpoints: built.map((b) => b.summary), appearanceGrid, priority };
}
