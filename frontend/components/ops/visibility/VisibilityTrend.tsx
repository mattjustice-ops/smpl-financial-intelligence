"use client";

import type {
  AnswerOutcome,
  CheckpointSummary,
  PriorityFrequency,
  TrialCell,
  VisibilityHistory,
} from "@/lib/aio/checkpoints";
import type { RecommendationLevel } from "@/lib/aio/visibility-score";

const REC_LABEL: Record<RecommendationLevel, string> = {
  none: "—",
  listed: "Listed",
  shortlisted: "Shortlisted",
  recommended: "Recommended",
  top_pick: "Top pick",
};

type Bar = { key: string; label: string; value: number; shown: string; bar: string; text: string; note?: string };

const HEADLINE_LEGEND = [
  { label: "Named as a product", bar: "bg-teal-400" },
  { label: "Shortlisted or recommended", bar: "bg-violet-400" },
];

const CITE_LEGEND = [
  { label: "Cited · visible source", bar: "bg-amber-400" },
  { label: "Cited · hidden “+N” only", bar: "border border-dashed border-amber-400/70 bg-amber-400/10" },
  { label: "Cited · visibility unknown (older capture, minimum)", bar: "bg-slate-500/60" },
];

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Date label per checkpoint, numbering runs that share a date ("Sep 29 · run 2"). */
function dateLabels(checkpoints: CheckpointSummary[]): (c: CheckpointSummary) => string {
  const byDate = new Map<string, string[]>();
  for (const c of checkpoints) {
    const d = shortDate(c.startedAt);
    byDate.set(d, [...(byDate.get(d) ?? []), c.key]);
  }
  return (c) => {
    const d = shortDate(c.startedAt);
    const same = byDate.get(d) ?? [];
    return same.length > 1 ? `${d} · run ${same.indexOf(c.key) + 1}` : d;
  };
}

function methodLabel(c: CheckpointSummary) {
  if (c.method === "capture_v2") return "Structured capture";
  if (c.method === "mixed") return "Mixed capture";
  return "Older capture";
}

const lb = (c: CheckpointSummary) => (c.citationIsLowerBound ? "≥" : "");

function headlineBars(c: CheckpointSummary): Bar[] {
  return [
    {
      key: "product",
      label: "Named as a product",
      value: c.namedAsProduct,
      shown: String(c.namedAsProduct),
      bar: "bg-teal-400",
      text: "text-teal-300",
    },
    {
      key: "shortlist",
      label: "Shortlisted or recommended",
      value: c.shortlistPlus,
      shown: String(c.shortlistPlus),
      bar: "bg-violet-400",
      text: "text-violet-300",
    },
  ];
}

function citationBars(c: CheckpointSummary): Bar[] {
  const bars: Bar[] = [];
  if (c.method !== "legacy") {
    bars.push(
      {
        key: "visible",
        label: "Cited · visible source",
        value: c.visibleCited,
        shown: String(c.visibleCited),
        bar: "bg-amber-400",
        text: "text-amber-300",
      },
      {
        key: "hidden",
        label: "Cited · hidden “+N” only",
        value: c.hiddenOnlyCited,
        shown: String(c.hiddenOnlyCited),
        bar: "border border-dashed border-amber-400/70 bg-amber-400/10",
        text: "text-amber-300/60",
      },
    );
  }
  if (!c.citationVisibilityKnown) {
    bars.push({
      key: "unknown",
      label: "Cited · visibility unknown",
      value: c.citedVisibilityUnknown,
      shown: `${lb(c)}${c.citedVisibilityUnknown}`,
      bar: "bg-slate-500/60",
      text: "text-slate-400",
      note: "older capture never collected hidden “+N” sources; minimum",
    });
  }
  return bars;
}

function BarColumn({ b, max, of }: { b: Bar; max: number; of: number }) {
  return (
    <div className="flex w-7 flex-col items-center justify-end">
      <span className={`mb-1 text-xs font-semibold ${b.text}`}>{b.shown}</span>
      <div
        className={`w-full rounded-t ${b.bar}`}
        style={{ height: `${Math.max(2, (b.value / max) * 112)}px` }}
        title={`${b.label}: ${b.shown} of ${of}${b.note ? ` (${b.note})` : ""}`}
      />
    </div>
  );
}

function TrendChart({ checkpoints }: { checkpoints: CheckpointSummary[] }) {
  const labelOf = dateLabels(checkpoints);
  const max = Math.max(4, ...checkpoints.flatMap((c) => [...headlineBars(c), ...citationBars(c)].map((b) => b.value)));
  return (
    <div className="mt-5">
      <div className="flex items-end gap-6 overflow-x-auto pb-2">
        {checkpoints.map((c) => (
          <div key={c.key} className="flex min-w-[170px] flex-1 flex-col items-center">
            <div className="flex h-36 items-end gap-2">
              {headlineBars(c).map((b) => (
                <BarColumn key={b.key} b={b} max={max} of={c.queries} />
              ))}
              <div className="mx-1 h-full w-px bg-white/10" />
              {citationBars(c).map((b) => (
                <BarColumn key={b.key} b={b} max={max} of={c.queries} />
              ))}
            </div>
            <div className="mt-2 text-center">
              <p className="text-sm font-medium text-white">{labelOf(c)}</p>
              <p className="text-[11px] text-slate-500">{methodLabel(c)}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
        {HEADLINE_LEGEND.map((o) => (
          <span key={o.label} className="flex items-center gap-1.5">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${o.bar}`} />
            {o.label}
          </span>
        ))}
        <span className="text-slate-600">|</span>
        <span className="text-slate-500">Diagnostics:</span>
        {CITE_LEGEND.map((o) => (
          <span key={o.label} className="flex items-center gap-1.5 text-slate-500">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${o.bar}`} />
            {o.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function CheckpointTable({ checkpoints }: { checkpoints: CheckpointSummary[] }) {
  const labelOf = dateLabels(checkpoints);
  const latest = checkpoints[checkpoints.length - 1];
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="pb-2 pr-4">Checkpoint</th>
            <th className="pb-2 pr-4">Named as product</th>
            <th className="pb-2 pr-4">Shortlisted+</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Visible cite</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Hidden “+N” cite</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Any mention</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Citation capture</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Informational ({latest.byClass.informational.queries})</th>
            <th className="pb-2 pr-4 font-normal text-slate-600">Vendor selection ({latest.byClass.vendor_selection.queries})</th>
            <th className="pb-2 font-normal text-slate-600">Originally reported</th>
          </tr>
        </thead>
        <tbody>
          {checkpoints.map((c) => (
            <tr key={c.key} className="border-t border-white/5 align-top">
              <td className="py-2.5 pr-4">
                <div className="text-slate-200">{labelOf(c)}</div>
                <div className="text-xs text-slate-500">{c.label}</div>
              </td>
              <td className="py-2.5 pr-4 font-medium text-teal-200">
                {c.namedAsProduct}/{c.queries}
              </td>
              <td className="py-2.5 pr-4 font-medium text-violet-200">
                {c.shortlistPlus}/{c.queries}
              </td>
              {c.method === "legacy" ? (
                <td colSpan={2} className="py-2.5 pr-4 text-slate-400">
                  {lb(c)}
                  {c.cited}/{c.queries} cited
                  <div className="text-xs text-slate-500">visibility unknown (older capture)</div>
                </td>
              ) : (
                <>
                  <td className="py-2.5 pr-4 text-amber-200/80">
                    {c.visibleCited}/{c.queries}
                  </td>
                  <td className="py-2.5 pr-4 text-amber-200/50">
                    {c.hiddenOnlyCited}/{c.queries}
                    {c.citedVisibilityUnknown ? (
                      <div className="text-xs text-slate-500">+{c.citedVisibilityUnknown} visibility unknown</div>
                    ) : null}
                  </td>
                </>
              )}
              <td className="py-2.5 pr-4 text-slate-400">
                {c.mentioned}/{c.queries}
              </td>
              <td className="py-2.5 pr-4 text-slate-400">
                {c.citationComplete}/{c.queries} complete
                <div className="text-xs text-slate-500">
                  {Object.entries(c.citationStatus)
                    .map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`)
                    .join(" · ")}
                </div>
              </td>
              <td className="py-2.5 pr-4 text-slate-400">
                product {c.byClass.informational.namedAsProduct} · cited {c.byClass.informational.cited}
              </td>
              <td className="py-2.5 pr-4 text-slate-400">
                product {c.byClass.vendor_selection.namedAsProduct} · shortlisted+{" "}
                {c.byClass.vendor_selection.shortlistPlus} · cited {c.byClass.vendor_selection.cited}
              </td>
              <td className="py-2.5 text-slate-500">
                {c.originalMentioned} mentioned · {c.originalCited} cited
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CitationBadge({ citation }: { citation: AnswerOutcome["citation"] }) {
  if (citation === "visible")
    return <span className="rounded bg-amber-400/15 px-1.5 py-0.5 text-[11px] text-amber-200">Visible cite</span>;
  if (citation === "hidden_only")
    return (
      <span className="rounded border border-dashed border-amber-400/40 px-1.5 py-0.5 text-[11px] text-amber-200/60">
        Hidden “+N” cite
      </span>
    );
  if (citation === "unknown")
    return <span className="rounded bg-slate-500/20 px-1.5 py-0.5 text-[11px] text-slate-300">Cited · visibility unknown</span>;
  return null;
}

function OutcomeBadges({ namedAsProduct, recommendation, mentioned, citation }: AnswerOutcome) {
  if (!mentioned && !namedAsProduct && citation === "none") return <span className="text-slate-600">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {namedAsProduct ? (
        <span className="rounded bg-teal-400/15 px-1.5 py-0.5 text-[11px] text-teal-200">
          Product · {REC_LABEL[recommendation]}
        </span>
      ) : mentioned ? (
        <span className="rounded bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-400">Passing mention</span>
      ) : null}
      <CitationBadge citation={citation} />
    </span>
  );
}

function AppearanceGrid({ history }: { history: VisibilityHistory }) {
  if (!history.appearanceGrid.length) return null;
  const labelOf = dateLabels(history.checkpoints);
  return (
    <div className="mt-8">
      <h3 className="text-sm font-semibold text-white">Where SMPL appeared</h3>
      <p className="mt-1 text-xs text-slate-500">
        Every query where SMPL was named as a product, mentioned in passing, or cited in any checkpoint. All other
        queries: no appearance yet.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="pb-2 pr-4">Query</th>
              {history.checkpoints.map((c) => (
                <th key={c.key} className="pb-2 pr-4 whitespace-nowrap">
                  {labelOf(c)}
                  <div className="font-normal normal-case text-slate-600">{methodLabel(c)}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.appearanceGrid.map((g) => (
              <tr key={g.queryId} className="border-t border-white/5">
                <td className="max-w-xs py-2 pr-4">
                  <div className="text-slate-200">{g.queryText || g.queryId}</div>
                  <div className="text-xs text-slate-500">
                    {g.queryId} · {g.queryClass.replace("_", " ")}
                  </div>
                </td>
                {g.cells.map((cell, i) => (
                  <td key={history.checkpoints[i].key} className="py-2 pr-4">
                    {cell ? <OutcomeBadges {...cell} /> : <span className="text-slate-600">not run</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const CITE_TEXT: Record<AnswerOutcome["citation"], string> = {
  none: "not cited",
  visible: "visible cite",
  hidden_only: "hidden “+N” cite only",
  unknown: "cited, visibility unknown",
};

function TrialDot({ t }: { t: TrialCell }) {
  const hit = t.namedAsProduct || t.citation !== "none";
  return (
    <div
      className={`flex h-9 w-10 flex-col items-center justify-center rounded-lg border text-[10px] leading-tight ${
        hit ? "border-teal-400/40 bg-teal-400/10" : "border-white/10 bg-white/[0.02]"
      }`}
      title={`Trial ${t.trial}: ${t.namedAsProduct ? `named as product (${REC_LABEL[t.recommendation]})` : t.mentioned ? "passing mention only" : "not named"}, ${CITE_TEXT[t.citation]}`}
    >
      <span className="text-slate-500">T{t.trial}</span>
      <span className="font-semibold">
        <span className={t.namedAsProduct ? "text-teal-300" : "text-slate-600"}>P</span>
        <span className={t.shortlistPlus ? "text-violet-300" : "text-slate-600"}>S</span>
        <span className={t.citation === "visible" ? "text-amber-300" : "text-slate-600"}>V</span>
        <span className={t.citation === "hidden_only" ? "text-amber-300/50" : "text-slate-600"}>H</span>
      </span>
    </div>
  );
}

function PriorityPanel({ priority }: { priority: PriorityFrequency }) {
  return (
    <div className="mt-8">
      <h3 className="text-sm font-semibold text-white">Priority queries · same-day repeat trials</h3>
      <p className="mt-1 text-xs text-slate-500">
        {priority.checkpointLabel}: each priority prompt run 3 times in fresh temporary chats. Trial 1 is the benchmark
        answer. Read these as frequencies — a single run can flip either way. Letters: P named as product · S
        shortlisted or recommended · V visible cite · H hidden “+N” cite.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {priority.queries.map((q) => (
          <div key={q.queryId} className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-sm text-slate-200" title={q.queryText}>
                {q.queryText || q.queryId}
              </div>
              <div className="text-xs text-slate-500">
                {q.queryId} · product {q.namedAsProduct}/{q.trials.length} · shortlisted+ {q.shortlistPlus}/
                {q.trials.length} · visible cite {q.visibleCited}/{q.trials.length} · hidden cite {q.hiddenOnlyCited}/
                {q.trials.length}
              </div>
            </div>
            <div className="flex shrink-0 gap-1.5">
              {q.trials.map((t) => (
                <TrialDot key={t.trial} t={t} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function VisibilityTrend({ history }: { history: VisibilityHistory }) {
  if (!history.checkpoints.length) return null;
  const prompts = history.checkpoints[history.checkpoints.length - 1].queries;
  return (
    <section className="mt-8 rounded-2xl border border-teal-500/20 bg-teal-500/[0.03] p-5">
      <p className="text-xs uppercase tracking-wide text-teal-300/80">ChatGPT benchmark · {prompts} prompts per checkpoint</p>
      <h2 className="mt-1 text-lg font-semibold text-white">Visibility trend</h2>
      <p className="mt-2 max-w-3xl text-sm text-slate-400">
        Every checkpoint re-scored with the current scorer. Left of the divider, the headline: SMPL <em>named as a
        software product</em> and SMPL <em>shortlisted or recommended</em>. Right of the divider, citation diagnostics:
        an SMPL page cited as a visible source, or only behind a “+N” button (outlined). Older captures never collected
        “+N” sources, so their citations can’t be split and are shown in grey as minimums.
      </p>
      <TrendChart checkpoints={history.checkpoints} />
      <CheckpointTable checkpoints={history.checkpoints} />
      <AppearanceGrid history={history} />
      {history.priority ? <PriorityPanel priority={history.priority} /> : null}
    </section>
  );
}

export function SmplPagesCited({ checkpoint }: { checkpoint: CheckpointSummary }) {
  return (
    <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
      <p className="text-xs uppercase tracking-wide text-amber-300/80">ChatGPT · latest checkpoint · diagnostic</p>
      <h2 className="mt-1 text-lg font-semibold text-white">SMPL pages cited as sources</h2>
      <p className="mt-1 text-xs text-slate-500">
        {shortDate(checkpoint.startedAt)} · {checkpoint.label}
      </p>
      {checkpoint.smplPages.length ? (
        <ul className="mt-4 space-y-2 text-sm">
          {checkpoint.smplPages.map((p) => (
            <li key={p.url} className="flex justify-between gap-3 border-b border-white/5 pb-1.5">
              <a href={p.url} target="_blank" rel="noreferrer" className="truncate text-teal-300 hover:underline">
                {p.url.replace(/^https:\/\/www\.smpl-ai\.com/, "") || "/"}
              </a>
              <span className="shrink-0 text-slate-400">
                {p.answers} answer{p.answers === 1 ? "" : "s"}
                {p.hiddenOnlyAnswers ? (
                  <span className="ml-1.5 rounded border border-dashed border-amber-400/40 px-1 text-[11px] text-amber-200/60">
                    {p.hiddenOnlyAnswers === p.answers ? "hidden “+N” only" : `${p.hiddenOnlyAnswers} hidden “+N” only`}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">No SMPL page URLs captured in this checkpoint.</p>
      )}
      <p className="mt-3 text-xs text-slate-500">
        Named as a product in {checkpoint.namedAsProduct} of {checkpoint.queries} answers · cited in {lb(checkpoint)}
        {checkpoint.cited}
        {checkpoint.citationVisibilityKnown
          ? ` (${checkpoint.visibleCited} visible, ${checkpoint.hiddenOnlyCited} hidden “+N” only)`
          : " (visibility unknown for older captures)"}
        . Being cited without being named means ChatGPT used SMPL content as background, not as a vendor.
      </p>
    </div>
  );
}
