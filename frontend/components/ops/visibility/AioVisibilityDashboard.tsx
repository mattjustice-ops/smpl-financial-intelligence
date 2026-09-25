"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type Overview = {
  query_count: number;
  audit_count: number;
  scored_audits: number;
  mention_rate: number;
  recommendation_rate: number;
  strong_recommendation_rate: number;
  citation_rate: number;
  owned_domain_citation_rate: number;
  avg_positioning_accuracy: number;
  share_of_voice: number;
  competitor_mentions: Array<{ name: string; count: number }>;
  recent_gaps: Array<{ query_id: string | null; query_text: string }>;
  disclosure: string;
  engine_diagnosis?: string;
  scoring_audit?: {
    batch_name: string;
    n: number;
    current_evaluator: string;
    note: string;
    stored: {
      mentions: number;
      shortlist_plus: number;
      owned_citations: number;
    };
    rules_v2: {
      mentions: number;
      shortlist_plus: number;
      owned_citations: number;
    };
    strength_changes: Array<{
      query_id: string | null;
      stored: string;
      rules_v2: string;
    }>;
  } | null;
  chatgpt_search_baseline?: {
    name: string;
    scorecard: {
      mention_rate: number;
      mention_count: number;
      citation_rate: number;
      owned_domain_citation_rate: number;
      categories_with_hit: number;
      categories_total: number;
      hit_query_id: string;
    };
  };
  google_genai_baseline?: {
    name: string;
    scorecard: {
      property_impressions: number;
      sept_1_to_14_impressions: number;
      sept_period_label?: string;
      last_7_days_impressions: number;
      peak_day: string;
      peak_day_impressions: number;
      pages_with_impressions: number;
      us_share: number;
      desktop_share: number;
      top_commercial_article: string;
      top_commercial_article_impressions: number;
    };
    top_pages: Array<{ url: string; impressions: number }>;
    interpretation: string;
  };
};

type QueryRow = {
  id: string;
  query_text: string;
  category: string;
  intent: string;
  priority: number;
  pulse_enabled?: boolean;
  target_page_hint: string | null;
};

type ContentRow = {
  id: string;
  url: string;
  title: string;
  content_type: string;
  status: string;
  hypothesis: string | null;
  primary_query_ids: string[];
  query_ids: string[];
};

type PulseOverview = {
  query_ids: string[];
  scored: number;
  mention_count: number;
  mention_rate: number;
  owned_citation_count: number;
  rows: Array<{
    query_id: string;
    query_text: string;
    smpl_mentioned: boolean;
    recommendation_strength: string;
    owned_cited: boolean;
  }>;
  sacred_baseline?: {
    name: string;
    scorecard: {
      mention_rate: number;
      mention_count: number;
      hit_query_id: string;
    };
  };
};

type AuditRow = {
  id: string;
  query_id: string | null;
  query_text: string;
  observed_at: string;
  raw_response: string;
  evaluation_json: {
    smpl_mentioned: boolean;
    recommendation_strength: string;
    smpl_owned_domain_cited: boolean;
    positioning_accuracy: number;
    competitors: Array<{ name: string }>;
    positioning_summary: string;
  };
};

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export function AioVisibilityDashboard() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [queries, setQueries] = useState<QueryRow[]>([]);
  const [audits, setAudits] = useState<AuditRow[]>([]);
  const [content, setContent] = useState<ContentRow[]>([]);
  const [pulse, setPulse] = useState<PulseOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const [queryId, setQueryId] = useState("");
  const [queryText, setQueryText] = useState("");
  const [rawResponse, setRawResponse] = useState("");
  const [citationsText, setCitationsText] = useState("");
  const [cleanSession, setCleanSession] = useState(true);
  const [batchName, setBatchName] = useState("");
  const [notes, setNotes] = useState("");

  const priorityQueries = useMemo(
    () => queries.filter((q) => q.priority >= 3),
    [queries],
  );
  const pulseQueries = useMemo(
    () => queries.filter((q) => q.pulse_enabled),
    [queries],
  );

  const refresh = useCallback(async () => {
    setError(null);
    const [o, q, a, c, p] = await Promise.all([
      fetch("/api/aio/overview").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || "overview failed");
        return j as Overview;
      }),
      fetch("/api/aio/queries?priorityMin=0").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || "queries failed");
        return j.queries as QueryRow[];
      }),
      fetch("/api/aio/audits").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || "audits failed");
        return j.audits as AuditRow[];
      }),
      fetch("/api/aio/content").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || "content failed");
        return j.content as ContentRow[];
      }),
      fetch("/api/aio/pulse").then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || "pulse failed");
        return j as PulseOverview;
      }),
    ]);
    setOverview(o);
    setQueries(q);
    setAudits(a);
    setContent(c);
    setPulse(p);
  }, []);

  useEffect(() => {
    void refresh().catch((e: Error) => setError(e.message));
  }, [refresh]);

  async function seed() {
    setBusy(true);
    setStatus(null);
    setError(null);
    try {
      const r = await fetch("/api/aio/overview", { method: "POST" });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "seed failed");
      setStatus(
        `Seeded ${j.seeded.queries} queries, ${j.seeded.competitors} competitors, ${j.seeded.content} content pages, ${j.seeded.content_maps} page→query maps, ${j.seeded.pulse_queries} pulse queries.`,
      );
      setOverview(j.overview);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitAudit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const r = await fetch("/api/aio/audits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          queryId: queryId || null,
          queryText,
          rawResponse,
          citationsText,
          cleanSessionConfirmed: cleanSession,
          batchName: batchName || undefined,
          notes,
          productNote: "ChatGPT Search (consumer)",
        }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "save failed");
      const ev = j.audit.evaluation_json;
      setStatus(
        `Saved. Mentioned=${ev.smpl_mentioned} · ${ev.recommendation_strength} · owned cite=${ev.smpl_owned_domain_cited} · positioning=${ev.positioning_accuracy}`,
      );
      setRawResponse("");
      setCitationsText("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  function pickQuery(id: string) {
    setQueryId(id);
    const q = queries.find((x) => x.id === id);
    if (q) setQueryText(q.query_text);
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 text-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-teal-300/80">
            SMPL Ops · Visibility
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-white">
            AIO Visibility
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Manual ChatGPT Search audits first. Paste clean-session answers;
            we score mention / recommendation / citations against brand truth.
            Not an OpenAI ranking score.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/app/ops"
            className="rounded-full border border-white/15 px-4 py-2 text-sm text-slate-300 hover:border-teal-400/40 hover:text-teal-200"
          >
            ← Ops
          </Link>
          <button
            type="button"
            disabled={busy}
            onClick={() => void seed()}
            className="rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
          >
            Seed queries
          </button>
        </div>
      </div>

      {error ? (
        <p className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </p>
      ) : null}
      {status ? (
        <p className="mt-4 rounded-xl border border-teal-500/30 bg-teal-500/10 px-4 py-3 text-sm text-teal-100">
          {status}
        </p>
      ) : null}

      {overview ? (
        <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Audits", String(overview.audit_count)],
            ["Mention rate", pct(overview.mention_rate)],
            ["Recommendation rate", pct(overview.recommendation_rate)],
            ["Owned-domain cite", pct(overview.owned_domain_citation_rate)],
            ["Strong recommend", pct(overview.strong_recommendation_rate)],
            ["Positioning avg", overview.avg_positioning_accuracy.toFixed(2)],
            ["Share of voice", pct(overview.share_of_voice)],
            ["Query bank", String(overview.query_count)],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4"
            >
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
            </div>
          ))}
        </section>
      ) : null}

      {overview?.disclosure ? (
        <p className="mt-3 text-xs text-slate-500">{overview.disclosure}</p>
      ) : null}

      {overview?.scoring_audit ? (
        <section className="mt-8 rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
          <p className="text-xs uppercase tracking-wide text-amber-300/80">
            Scoring audit · {overview.scoring_audit.current_evaluator}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-white">
            Stored vs live rescore — {overview.scoring_audit.batch_name}
          </h2>
          <p className="mt-2 text-xs text-slate-500">
            {overview.scoring_audit.note}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {(
              [
                ["Mentions", "mentions"],
                ["Shortlist+", "shortlist_plus"],
                ["Owned cites", "owned_citations"],
              ] as const
            ).map(([label, key]) => (
              <div
                key={key}
                className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3"
              >
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-1 text-sm text-slate-300">
                  Stored{" "}
                  <span className="font-semibold text-white">
                    {overview.scoring_audit!.stored[key]}
                  </span>
                  {" → "}
                  <span className="font-semibold text-amber-200">
                    v2 {overview.scoring_audit!.rules_v2[key]}
                  </span>
                  <span className="text-slate-500">
                    {" "}
                    / {overview.scoring_audit!.n}
                  </span>
                </p>
              </div>
            ))}
          </div>
          {overview.scoring_audit.strength_changes.length ? (
            <ul className="mt-4 space-y-1 text-xs text-slate-400">
              {overview.scoring_audit.strength_changes.map((c) => (
                <li key={`${c.query_id}-${c.stored}-${c.rules_v2}`}>
                  <span className="text-slate-300">{c.query_id || "?"}</span>
                  : {c.stored} → {c.rules_v2}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs text-slate-500">
              No strength deltas vs stored labels for this batch.
            </p>
          )}
        </section>
      ) : null}

      {overview?.chatgpt_search_baseline || overview?.google_genai_baseline ? (
        <section className="mt-8 grid gap-4 lg:grid-cols-2">
          {overview.chatgpt_search_baseline ? (
            <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.04] p-5">
              <p className="text-xs uppercase tracking-wide text-rose-300/80">
                Controlled benchmark
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                {overview.chatgpt_search_baseline.name}
              </h2>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Mentions</dt>
                  <dd className="font-medium text-white">
                    {overview.chatgpt_search_baseline.scorecard.mention_count}
                    /46 ({pct(overview.chatgpt_search_baseline.scorecard.mention_rate)})
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Citation rate</dt>
                  <dd className="font-medium text-white">
                    {pct(overview.chatgpt_search_baseline.scorecard.citation_rate)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Owned-domain cite</dt>
                  <dd className="font-medium text-white">
                    {pct(
                      overview.chatgpt_search_baseline.scorecard
                        .owned_domain_citation_rate,
                    )}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Categories with hit</dt>
                  <dd className="font-medium text-white">
                    {
                      overview.chatgpt_search_baseline.scorecard
                        .categories_with_hit
                    }
                    /
                    {
                      overview.chatgpt_search_baseline.scorecard
                        .categories_total
                    }
                  </dd>
                </div>
                <div className="flex justify-between gap-3 py-1.5">
                  <dt className="text-slate-400">Only hit</dt>
                  <dd className="font-medium text-white">
                    {overview.chatgpt_search_baseline.scorecard.hit_query_id}
                  </dd>
                </div>
              </dl>
              <p className="mt-3 text-xs text-slate-500">
                Not yet classifiable / shortlisted in ChatGPT Search.
              </p>
            </div>
          ) : null}

          {overview.google_genai_baseline ? (
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-5">
              <p className="text-xs uppercase tracking-wide text-emerald-300/80">
                Search Console · Generative AI
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                {overview.google_genai_baseline.name}
              </h2>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Property impressions</dt>
                  <dd className="font-medium text-white">
                    {
                      overview.google_genai_baseline.scorecard
                        .property_impressions
                    }
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">
                    {overview.google_genai_baseline.scorecard
                      .sept_period_label || "Sept 1–14"}
                  </dt>
                  <dd className="font-medium text-white">
                    {
                      overview.google_genai_baseline.scorecard
                        .sept_1_to_14_impressions
                    }
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Last 7 days in file</dt>
                  <dd className="font-medium text-white">
                    {
                      overview.google_genai_baseline.scorecard
                        .last_7_days_impressions
                    }
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                  <dt className="text-slate-400">Best FP&A article</dt>
                  <dd className="font-medium text-white">
                    {
                      overview.google_genai_baseline.scorecard
                        .top_commercial_article_impressions
                    }{" "}
                    impressions
                  </dd>
                </div>
                <div className="flex justify-between gap-3 py-1.5">
                  <dt className="text-slate-400">US / desktop</dt>
                  <dd className="font-medium text-white">
                    {pct(overview.google_genai_baseline.scorecard.us_share)} /{" "}
                    {pct(overview.google_genai_baseline.scorecard.desktop_share)}
                  </dd>
                </div>
              </dl>
              <ul className="mt-3 space-y-1 text-xs text-slate-400">
                {overview.google_genai_baseline.top_pages
                  .slice(0, 4)
                  .map((p) => (
                    <li key={p.url} className="flex justify-between gap-2">
                      <span className="truncate">
                        {p.url.replace("https://www.smpl-ai.com", "") || "/"}
                      </span>
                      <span className="shrink-0 text-slate-300">
                        {p.impressions}
                      </span>
                    </li>
                  ))}
              </ul>
              <p className="mt-3 text-xs text-slate-500">
                Becoming retrievable in Google generative features. Impressions
                only — no query or AI-click breakdown in this export.
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      {overview?.engine_diagnosis ? (
        <p className="mt-3 text-sm text-teal-200/90">
          {overview.engine_diagnosis}
        </p>
      ) : null}

      {pulse ? (
        <section className="mt-8 rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">
                Weekly 12-query pulse
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Frozen wording. Latest audit per pulse query vs sacred baseline{" "}
                <span className="text-amber-200/90">
                  {pulse.sacred_baseline?.name ||
                    "ChatGPT Search Baseline 2026-09-15"}
                </span>
                .
              </p>
            </div>
            <div className="text-right text-sm text-slate-300">
              <div>
                Pulse mention{" "}
                <span className="font-semibold text-white">
                  {pulse.mention_count}/{pulse.query_ids.length} (
                  {pct(pulse.mention_rate)})
                </span>
              </div>
              <div className="text-slate-500">
                Baseline{" "}
                {pulse.sacred_baseline
                  ? `${pulse.sacred_baseline.scorecard.mention_count}/46 (${pct(pulse.sacred_baseline.scorecard.mention_rate)})`
                  : "2.2%"}
              </div>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2 pr-4">Query</th>
                  <th className="pb-2 pr-4">Mention</th>
                  <th className="pb-2 pr-4">Strength</th>
                  <th className="pb-2">Owned cite</th>
                </tr>
              </thead>
              <tbody>
                {pulse.rows.map((r) => (
                  <tr key={r.query_id} className="border-t border-white/5">
                    <td className="py-2 pr-4 text-slate-300">
                      <span className="text-xs text-slate-500">
                        {r.query_id}
                      </span>
                      <div>{r.query_text}</div>
                    </td>
                    <td className="py-2 pr-4">
                      {r.smpl_mentioned ? "Yes" : "No"}
                    </td>
                    <td className="py-2 pr-4">{r.recommendation_strength}</td>
                    <td className="py-2">{r.owned_cited ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pulseQueries.length ? (
            <p className="mt-3 text-xs text-slate-500">
              Capture pulse audits with batch name like{" "}
              <code className="text-slate-400">
                Weekly pulse - YYYY-MM-DD
              </code>
              .
            </p>
          ) : null}
        </section>
      ) : null}

      <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <h2 className="text-lg font-semibold text-white">
          Content registry (page → query hypotheses)
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Every strategic page should declare which benchmark queries it is
          meant to move. Seed via “Seed queries”.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-2 pr-4">Page</th>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Primary queries</th>
                <th className="pb-2">Hypothesis</th>
              </tr>
            </thead>
            <tbody>
              {content.map((c) => (
                <tr key={c.id} className="border-t border-white/5 align-top">
                  <td className="py-3 pr-4">
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-teal-300 hover:underline"
                    >
                      {c.title}
                    </a>
                    <div className="text-xs text-slate-500">{c.status}</div>
                  </td>
                  <td className="py-3 pr-4 text-slate-400">{c.content_type}</td>
                  <td className="py-3 pr-4 text-slate-400">
                    {c.primary_query_ids.length
                      ? c.primary_query_ids.join(", ")
                      : "—"}
                  </td>
                  <td className="py-3 max-w-md text-slate-400">
                    {c.hypothesis || "—"}
                  </td>
                </tr>
              ))}
              {!content.length ? (
                <tr>
                  <td colSpan={4} className="py-6 text-slate-500">
                    No content registered yet. Click “Seed queries”.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10 grid gap-8 lg:grid-cols-2">
        <form
          onSubmit={(e) => void submitAudit(e)}
          className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
        >
          <h2 className="text-lg font-semibold text-white">
            Capture ChatGPT Search audit
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Use a clean chat (no memory of SMPL). Enable Search. Paste the full
            answer and any citation URLs.
          </p>

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Seed query (priority 3 shown first)
          </label>
          <select
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm"
            value={queryId}
            onChange={(e) => pickQuery(e.target.value)}
          >
            <option value="">Custom / freeform</option>
            {priorityQueries.map((q) => (
              <option key={q.id} value={q.id}>
                [{q.priority}] {q.category}: {q.query_text.slice(0, 80)}
              </option>
            ))}
            {queries
              .filter((q) => q.priority < 3)
              .map((q) => (
                <option key={q.id} value={q.id}>
                  [{q.priority}] {q.category}: {q.query_text.slice(0, 80)}
                </option>
              ))}
          </select>

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Exact query used
          </label>
          <textarea
            required
            rows={2}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
          />

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Pasted ChatGPT answer
          </label>
          <textarea
            required
            rows={10}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm font-mono"
            value={rawResponse}
            onChange={(e) => setRawResponse(e.target.value)}
          />

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Citation URLs (optional, one per line)
          </label>
          <textarea
            rows={3}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm font-mono"
            value={citationsText}
            onChange={(e) => setCitationsText(e.target.value)}
          />

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Batch name (optional)
          </label>
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Baseline - 2026-09-15"
            value={batchName}
            onChange={(e) => setBatchName(e.target.value)}
          />

          <label className="mt-4 block text-xs uppercase tracking-wide text-slate-500">
            Notes
          </label>
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <label className="mt-4 flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={cleanSession}
              onChange={(e) => setCleanSession(e.target.checked)}
            />
            Clean session confirmed (no prior SMPL context)
          </label>

          <button
            type="submit"
            disabled={busy}
            className="mt-5 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50"
          >
            Score &amp; save audit
          </button>
        </form>

        <div className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="text-lg font-semibold text-white">
              Competitor mentions (from audits)
            </h2>
            {overview?.competitor_mentions?.length ? (
              <ul className="mt-3 space-y-1 text-sm">
                {overview.competitor_mentions.slice(0, 12).map((c) => (
                  <li
                    key={c.name}
                    className="flex justify-between border-b border-white/5 py-1.5"
                  >
                    <span>{c.name}</span>
                    <span className="text-slate-400">{c.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-slate-500">No audits yet.</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="text-lg font-semibold text-white">
              Recent gaps (SMPL absent)
            </h2>
            {overview?.recent_gaps?.length ? (
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {overview.recent_gaps.map((g, i) => (
                  <li key={`${g.query_id}-${i}`} className="text-slate-400">
                    {g.query_text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                No gaps recorded yet (or SMPL appeared in all recent audits).
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <h2 className="text-lg font-semibold text-white">Recent audits</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-2 pr-4">When</th>
                <th className="pb-2 pr-4">Query</th>
                <th className="pb-2 pr-4">Mention</th>
                <th className="pb-2 pr-4">Strength</th>
                <th className="pb-2 pr-4">Owned cite</th>
                <th className="pb-2">Positioning</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((a) => (
                <tr key={a.id} className="border-t border-white/5 align-top">
                  <td className="py-3 pr-4 text-slate-500 whitespace-nowrap">
                    {new Date(a.observed_at).toLocaleString()}
                  </td>
                  <td className="py-3 pr-4 max-w-md text-slate-300">
                    {a.query_text}
                  </td>
                  <td className="py-3 pr-4">
                    {a.evaluation_json.smpl_mentioned ? "Yes" : "No"}
                  </td>
                  <td className="py-3 pr-4">
                    {a.evaluation_json.recommendation_strength}
                  </td>
                  <td className="py-3 pr-4">
                    {a.evaluation_json.smpl_owned_domain_cited ? "Yes" : "No"}
                  </td>
                  <td className="py-3">
                    {a.evaluation_json.positioning_accuracy}
                  </td>
                </tr>
              ))}
              {!audits.length ? (
                <tr>
                  <td colSpan={6} className="py-6 text-slate-500">
                    No audits yet. Seed queries, then capture your first clean
                    ChatGPT Search answer.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
