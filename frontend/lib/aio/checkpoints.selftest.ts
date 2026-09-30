import { MIN_CHECKPOINT_QUERIES, REPEAT_SOURCE_TYPE, buildVisibilityHistory, type CheckpointAuditRow } from "./checkpoints";
import type { CitedSource } from "./visibility-score";

let failures = 0;
function check(cond: unknown, msg: string) {
  if (!cond) {
    failures += 1;
    console.error("FAIL:", msg);
  }
}

const ids = Array.from({ length: MIN_CHECKPOINT_QUERIES }, (_, i) => `q_${String(i).padStart(2, "0")}`);
const row = (over: Partial<CheckpointAuditRow>): CheckpointAuditRow => ({
  batch_name: "Full 46 - 2026-10-01",
  batch_source_type: "manual_chatgpt",
  query_id: "q_00",
  observed_at: "2026-10-01T10:00:00Z",
  raw_response: "Consider Pigment or Cube.",
  citations_json: [],
  capture_json: null,
  evaluation_json: { smpl_mentioned: false, smpl_cited: false },
  ...over,
});
const SMPL_PAGE = "https://www.smpl-ai.com/blog/x?utm_source=chatgpt.com";
const capture = (
  runId: string,
  trial: number | null,
  opts: { sources?: CitedSource[]; labels?: string[]; prose?: string } = {},
) => ({
  schema: "aio_capture_v2" as const,
  runId,
  key: `k${trial}`,
  trial,
  phase: trial && trial > 1 ? "priority_repeat" : "benchmark",
  proseText: opts.prose ?? "Consider Pigment or Cube.",
  citationLabels: opts.labels ?? [],
  sources: opts.sources ?? [],
  citationStatus: "complete" as const,
});
const structuredCapture = (id: string) => {
  if (id === "q_05") return capture("run-b", 1);
  // Hidden-only citation: SMPL page appears only behind a "+N" pill.
  if (id === "q_03") return capture("run-b", null, { sources: [{ url: SMPL_PAGE, publisher: "SMPL.ai", hidden: true }] });
  // Visible citation: SMPL pill on screen.
  if (id === "q_04") return capture("run-b", null, { labels: ["SMPL.ai"], sources: [{ url: SMPL_PAGE, publisher: "SMPL.ai" }] });
  // Passing reference: SMPL is the author of advice, not a vendor option.
  if (id === "q_06") {
    return capture("run-b", null, { prose: "According to SMPL.ai, the board pack should tie ARR to GAAP revenue first." });
  }
  if (id === "q_07") return capture("run-b", null, { prose: "I'd start the evaluation with Cube, Pigment, and SMPL.ai." });
  return capture("run-b", null);
};

const rows: CheckpointAuditRow[] = [
  // Legacy checkpoint split across a continued batch; q_00 captured twice (latest wins).
  ...ids.map((id, i) =>
    row({ batch_name: i < 20 ? "Baseline - 2026-09-01" : "Baseline - 2026-09-01 (cont)", query_id: id, observed_at: "2026-09-01T10:00:00Z" }),
  ),
  row({
    batch_name: "Baseline - 2026-09-01",
    query_id: "q_00",
    observed_at: "2026-09-01T11:00:00Z",
    raw_response: "One newer option worth knowing about is SMPL.ai.",
  }),
  // Legacy citation pill: cited, but hidden "+N" sources were never collected.
  row({
    batch_name: "Baseline - 2026-09-01",
    query_id: "q_02",
    observed_at: "2026-09-01T11:00:00Z",
    raw_response: "Driver-based forecasting matters for SaaS. \nSMPL.ai\n+1",
    citations_json: [SMPL_PAGE],
  }),
  // A small ad-hoc batch is not a checkpoint.
  row({ batch_name: "Manual spot check", query_id: "q_01", observed_at: "2026-09-05T10:00:00Z", raw_response: "SMPL.ai is a top pick." }),
  // Structured checkpoint plus repeat trials of q_05.
  ...ids.map((id) => row({ query_id: id, capture_json: structuredCapture(id) })),
  row({
    batch_source_type: REPEAT_SOURCE_TYPE,
    query_id: "q_05",
    observed_at: "2026-10-01T11:00:00Z",
    capture_json: capture("run-b", 2, { sources: [{ url: SMPL_PAGE }] }),
  }),
  row({
    batch_source_type: REPEAT_SOURCE_TYPE,
    query_id: "q_05",
    observed_at: "2026-10-01T12:00:00Z",
    capture_json: capture("run-b", 3, { sources: [{ url: SMPL_PAGE, hidden: true }] }),
  }),
];

const h = buildVisibilityHistory(rows, ["q_05"]);
check(h.checkpoints.length === 2, `two checkpoints expected, got ${h.checkpoints.map((c) => c.key)}`);
const [legacy, structured] = h.checkpoints;
check(legacy?.key === "Baseline - 2026-09-01" && legacy.queries === MIN_CHECKPOINT_QUERIES, "(cont) batch merged into one checkpoint");
check(
  legacy?.namedAsProduct === 1 && legacy.mentioned === 1 && legacy.method === "legacy" && legacy.citationIsLowerBound,
  "latest duplicate wins; legacy citations are a lower bound",
);
check(
  legacy && !legacy.citationVisibilityKnown && legacy.cited === 1 && legacy.citedVisibilityUnknown === 1,
  "legacy checkpoint: citation visibility unknown",
);
check(legacy?.visibleCited === 0 && legacy.hiddenOnlyCited === 0, "legacy citation is not guessed as visible or hidden");
check(structured?.method === "capture_v2" && !structured.citationIsLowerBound, "structured checkpoint has complete citations");
check(structured?.citationVisibilityKnown && structured.citedVisibilityUnknown === 0, "structured checkpoint: visibility known");
check(structured?.queries === MIN_CHECKPOINT_QUERIES && structured.cited === 2, "repeat trials excluded from checkpoint counts");
check(structured?.visibleCited === 1 && structured.hiddenOnlyCited === 1, "visible vs hidden-only citations split");
check(
  structured?.namedAsProduct === 1 && structured.shortlistPlus === 1,
  `hidden-only citation and passing reference do not raise headline counts, got ${structured?.namedAsProduct}/${structured?.shortlistPlus}`,
);
check(structured?.mentioned === 2, "passing reference still counts as a prose mention diagnostic");
const hiddenPage = structured?.smplPages.find((p) => p.url === "https://www.smpl-ai.com/blog/x");
check(hiddenPage?.answers === 2 && hiddenPage.hiddenOnlyAnswers === 1, "SMPL page tracks hidden-only answers");
check(structured?.byClass.informational.queries === 1, "query class split");
const q5 = h.priority?.queries.find((q) => q.queryId === "q_05");
check(h.priority?.checkpointKey === structured?.key && q5?.trials.length === 3, "repeats pair with the checkpoint of the same run");
check(
  q5?.visibleCited === 1 && q5.hiddenOnlyCited === 1 && q5.namedAsProduct === 0 && q5.trials.map((t) => t.trial).join() === "1,2,3",
  "trial frequency counted per trial with visible/hidden split",
);
check(h.appearanceGrid.some((g) => g.queryId === "q_00") && !h.appearanceGrid.some((g) => g.queryId === "q_01"), "grid ignores non-checkpoint batches");
const q06 = h.appearanceGrid.find((g) => g.queryId === "q_06")?.cells[1];
check(q06?.mentioned && !q06.namedAsProduct, "grid: passing reference is a mention, not a product");

// Ordering is independent of input row order: same-instant duplicates resolve by id, and priority
// queries follow the supplied design order, not the order repeats happened to be returned in.
const tieRows: CheckpointAuditRow[] = [
  ...rows.map((r, i) => ({ ...r, id: `id-${String(i).padStart(3, "0")}` })),
  row({
    id: "id-z1",
    query_id: "q_10",
    raw_response: "SMPL.ai is a top pick.",
    capture_json: capture("run-b", null, { prose: "SMPL.ai is a top pick." }),
  }),
  row({ id: "id-a1", query_id: "q_10", capture_json: capture("run-b", null) }),
  ...["q_09", "q_08"].map((id, i) =>
    row({ id: `id-r${i}`, batch_source_type: REPEAT_SOURCE_TYPE, query_id: id, capture_json: capture("run-b", 2) }),
  ),
];
const order = ["q_09", "q_05", "q_08"];
const fwd = buildVisibilityHistory(tieRows, ["q_05"], order);
const rev = buildVisibilityHistory([...tieRows].reverse(), ["q_05"], order);
check(JSON.stringify(fwd) === JSON.stringify(rev), "history is identical regardless of input row order");
check(fwd.checkpoints[1]?.namedAsProduct === 2, "same-instant duplicate: highest id wins as the latest answer");
check(
  fwd.priority?.queries.map((q) => q.queryId).join() === "q_09,q_05,q_08",
  `priority queries follow design order, got ${fwd.priority?.queries.map((q) => q.queryId)}`,
);

if (failures) {
  console.error(`${failures} checkpoint check(s) failed`);
  process.exit(1);
}
console.log("checkpoint checks ok");
