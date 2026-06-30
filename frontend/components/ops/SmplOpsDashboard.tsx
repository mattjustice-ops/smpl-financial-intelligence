"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type TabId = "usage" | "health";

type CustomerUsageResponse = {
  period_days: number;
  generated_at: string;
  totals: {
    ai_cost_usd: number;
    input_tokens: number;
    output_tokens: number;
    llm_calls: number;
    exports_complete: number;
    active_organizations: number;
  };
  customers: Array<{
    organization_id: string | null;
    organization_name: string;
    plan: string | null;
    status: string | null;
    ai_cost_usd: number;
    input_tokens: number;
    output_tokens: number;
    llm_calls: number;
    exports_complete: number;
  }>;
};

type PlatformHealthResponse = {
  generated_at: string;
  database: { ok: boolean; latency_ms: number | null };
  export_jobs: {
    active_count: number;
    jobs: Array<{
      job_id: string;
      kind: string;
      status: string;
      message: string;
      organization_id: string | null;
      error: string | null;
      age_seconds: number;
      running_seconds: number | null;
    }>;
  };
  last_24h: {
    llm_calls: number;
    ai_cost_usd: number;
    export_failures: number;
  };
  recent_events: Array<{
    event_type: string;
    feature: string | null;
    organization_id: string | null;
    created_at: string;
    metadata: Record<string, unknown> | null;
  }>;
};

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
}

function formatInt(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function statusPill(ok: boolean): string {
  return ok
    ? "border-teal-400/40 bg-teal-400/10 text-teal-300"
    : "border-rose-400/40 bg-rose-400/10 text-rose-300";
}

function jobStatusClass(status: string): string {
  if (status === "complete") return "text-teal-300";
  if (status === "failed") return "text-rose-300";
  if (status === "running") return "text-amber-300";
  return "text-slate-400";
}

export function SmplOpsDashboard() {
  const [tab, setTab] = useState<TabId>("usage");
  const [usage, setUsage] = useState<CustomerUsageResponse | null>(null);
  const [health, setHealth] = useState<PlatformHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageRes, healthRes] = await Promise.all([
        fetch("/api/ops/customer-usage?days=30", { cache: "no-store" }),
        fetch("/api/ops/platform-health", { cache: "no-store" }),
      ]);
      if (!usageRes.ok) {
        throw new Error(`Customer usage API returned ${usageRes.status}`);
      }
      if (!healthRes.ok) {
        throw new Error(`Platform health API returned ${healthRes.status}`);
      }
      setUsage((await usageRes.json()) as CustomerUsageResponse);
      setHealth((await healthRes.json()) as PlatformHealthResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 md:py-14">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-400">
            Internal · SMPL Ops
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Customer usage &amp; platform health
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-400">
            AI spend and export volume by workspace, plus live export jobs and database latency.
            Data comes from <code className="text-slate-300">usage_events</code> in Neon.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            href="/app"
            className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            Back to app
          </Link>
        </div>
      </div>

      <div className="mb-8 flex gap-2 border-b border-white/10 pb-1">
        {(
          [
            ["usage", "Customer usage"],
            ["health", "Platform health"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium transition ${
              tab === id
                ? "border border-b-0 border-white/15 bg-slate-900 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="mb-6 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {loading && !usage && !health ? (
        <p className="text-sm text-slate-400">Loading SMPL Ops…</p>
      ) : null}

      {tab === "usage" && usage ? (
        <section className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["AI spend (30d)", formatUsd(usage.totals.ai_cost_usd)],
              ["LLM calls", formatInt(usage.totals.llm_calls)],
              ["Exports completed", formatInt(usage.totals.exports_complete)],
              ["Active orgs", formatInt(usage.totals.active_organizations)],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-xl border border-white/10 bg-slate-900/60 p-4"
              >
                <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{value}</p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-widest text-slate-400">
                <tr>
                  <th className="px-4 py-3">Organization</th>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3 text-right">AI $</th>
                  <th className="px-4 py-3 text-right">Tokens in/out</th>
                  <th className="px-4 py-3 text-right">LLM calls</th>
                  <th className="px-4 py-3 text-right">Exports</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {usage.customers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                      No usage recorded yet. Run a board export with AI commentary to seed data.
                    </td>
                  </tr>
                ) : (
                  usage.customers.map((row) => (
                    <tr key={row.organization_id ?? row.organization_name}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-white">{row.organization_name}</div>
                        <div className="text-xs text-slate-500">{row.organization_id}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{row.plan ?? "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatUsd(row.ai_cost_usd)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {formatInt(row.input_tokens)} / {formatInt(row.output_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatInt(row.llm_calls)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatInt(row.exports_complete)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {tab === "health" && health ? (
        <section className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Database</p>
              <p className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusPill(health.database.ok)}`}
                >
                  {health.database.ok ? "Connected" : "Error"}
                </span>
                {health.database.latency_ms != null ? (
                  <span className="text-sm text-slate-400">{health.database.latency_ms} ms</span>
                ) : null}
              </p>
            </div>
            {[
              ["LLM calls (24h)", formatInt(health.last_24h.llm_calls)],
              ["AI $ (24h)", formatUsd(health.last_24h.ai_cost_usd)],
              ["Export failures (24h)", formatInt(health.last_24h.export_failures)],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-xl border border-white/10 bg-slate-900/60 p-4"
              >
                <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">
                Export jobs (in-memory, this API instance)
              </h2>
              <span className="text-xs text-slate-500">
                {health.export_jobs.active_count} active
              </span>
            </div>
            {health.export_jobs.jobs.length === 0 ? (
              <p className="text-sm text-slate-500">No export jobs in the last hour.</p>
            ) : (
              <ul className="divide-y divide-white/5 text-sm">
                {health.export_jobs.jobs.map((job) => (
                  <li key={job.job_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
                    <span className={`font-medium ${jobStatusClass(job.status)}`}>
                      {job.status}
                    </span>
                    <span className="text-slate-300">{job.kind}</span>
                    <span className="text-slate-500">{job.message}</span>
                    {job.running_seconds != null ? (
                      <span className="text-amber-300/80">{job.running_seconds}s running</span>
                    ) : null}
                    {job.error ? (
                      <span className="text-rose-300/90 truncate max-w-md">{job.error}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">Recent failures &amp; checks</h2>
            {health.recent_events.length === 0 ? (
              <p className="text-sm text-slate-500">No recent export failures.</p>
            ) : (
              <ul className="divide-y divide-white/5 text-sm text-slate-300">
                {health.recent_events.map((event, index) => (
                  <li key={`${event.created_at}-${index}`} className="py-2">
                    <span className="text-slate-400">{event.created_at}</span>
                    {" · "}
                    <span className="text-white">{event.event_type}</span>
                    {event.feature ? ` · ${event.feature}` : ""}
                    {event.metadata?.error ? (
                      <span className="block text-rose-300/90">{String(event.metadata.error)}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}
    </main>
  );
}
