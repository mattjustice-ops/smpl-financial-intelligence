"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type TabId = "usage" | "health";

type CustomerUsageResponse = {
  period: {
    kind: "calendar_month" | "rolling_days";
    month?: string;
    days?: number;
    start: string;
    end: string;
  };
  available_months: string[];
  generated_at: string;
  totals: {
    ai_cost_usd: number;
    input_tokens: number;
    output_tokens: number;
    llm_calls: number;
    exports_complete: number;
    active_organizations: number;
    estimated_storage_mb: number;
    database_gb?: number;
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
    warehouse_rows: number;
    estimated_storage_mb: number;
  }>;
};

type PlatformHealthResponse = {
  generated_at: string;
  database: { ok: boolean; latency_ms: number | null };
  storage: {
    database_gb?: number;
    tenant_table_gb?: number;
    captured_at?: string;
    top_tables: Array<{ table: string; size_mb: number }>;
    history: Array<{ captured_at: string; database_gb?: number; tenant_table_gb?: number }>;
  };
  alerts: {
    status: string;
    last_check_at: string | null;
    checks: Array<{ name: string; ok: boolean; detail?: string; latency_ms?: number }>;
  };
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

function formatMb(value: number): string {
  if (value >= 1024) {
    return `${(value / 1024).toFixed(2)} GB`;
  }
  return `${value.toFixed(1)} MB`;
}

function formatMonthLabel(month: string): string {
  const [year, mon] = month.split("-").map(Number);
  const date = new Date(Date.UTC(year, mon - 1, 1));
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

function statusPill(ok: boolean): string {
  return ok
    ? "border-teal-400/40 bg-teal-400/10 text-teal-300"
    : "border-rose-400/40 bg-rose-400/10 text-rose-300";
}

function alertStatusClass(status: string): string {
  if (status === "ok") return "text-teal-300";
  if (status === "degraded") return "text-amber-300";
  return "text-slate-400";
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
  const [periodMode, setPeriodMode] = useState<"month" | "rolling">("month");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [rollingDays, setRollingDays] = useState(30);

  const monthOptions = useMemo(() => {
    const fromApi = usage?.available_months ?? health ? [] : [];
    if (fromApi.length > 0) return fromApi;
    const now = new Date();
    const months: string[] = [];
    for (let i = 0; i < 12; i += 1) {
      const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
      months.push(
        `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`,
      );
    }
    return months;
  }, [usage?.available_months, health]);

  useEffect(() => {
    if (!selectedMonth && monthOptions.length > 0) {
      setSelectedMonth(monthOptions[0]!);
    }
  }, [monthOptions, selectedMonth]);

  const usageQuery = useMemo(() => {
    if (periodMode === "month" && selectedMonth) {
      return `month=${encodeURIComponent(selectedMonth)}`;
    }
    return `days=${rollingDays}`;
  }, [periodMode, selectedMonth, rollingDays]);

  const periodLabel = useMemo(() => {
    if (!usage) return "";
    if (usage.period.kind === "calendar_month" && usage.period.month) {
      return formatMonthLabel(usage.period.month);
    }
    return `Last ${usage.period.days ?? rollingDays} days`;
  }, [usage, rollingDays]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageRes, healthRes] = await Promise.all([
        fetch(`/api/ops/customer-usage?${usageQuery}`, { cache: "no-store" }),
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
  }, [usageQuery]);

  useEffect(() => {
    void load();
  }, [load]);

  const runHealthCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/ops/run-health-check", { method: "POST", cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Health check API returned ${res.status}`);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  };

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
            AI spend, Neon storage footprint, and export volume by workspace — calendar months
            roll forward automatically. Storage snapshots refresh about once per day.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          {tab === "health" ? (
            <button
              type="button"
              onClick={() => void runHealthCheck()}
              disabled={loading}
              className="rounded-lg border border-teal-400/30 bg-teal-400/10 px-3 py-2 text-sm text-teal-200 hover:bg-teal-400/20 disabled:opacity-50"
            >
              Run health check
            </button>
          ) : null}
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
          <div className="flex flex-wrap items-end gap-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">Period</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setPeriodMode("month")}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    periodMode === "month"
                      ? "bg-white/10 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Calendar month
                </button>
                <button
                  type="button"
                  onClick={() => setPeriodMode("rolling")}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    periodMode === "rolling"
                      ? "bg-white/10 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Rolling window
                </button>
              </div>
            </div>
            {periodMode === "month" ? (
              <label className="text-sm text-slate-400">
                Month
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="ml-2 rounded-md border border-white/15 bg-slate-950 px-2 py-1.5 text-white"
                >
                  {monthOptions.map((month) => (
                    <option key={month} value={month}>
                      {formatMonthLabel(month)}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="text-sm text-slate-400">
                Days
                <select
                  value={rollingDays}
                  onChange={(e) => setRollingDays(Number(e.target.value))}
                  className="ml-2 rounded-md border border-white/15 bg-slate-950 px-2 py-1.5 text-white"
                >
                  {[7, 30, 60, 90].map((days) => (
                    <option key={days} value={days}>
                      {days}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <p className="text-xs text-slate-500">Showing {periodLabel}</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {[
              ["AI spend", formatUsd(usage.totals.ai_cost_usd)],
              ["LLM calls", formatInt(usage.totals.llm_calls)],
              ["Exports", formatInt(usage.totals.exports_complete)],
              ["Est. warehouse", formatMb(usage.totals.estimated_storage_mb)],
              [
                "Neon total",
                usage.totals.database_gb != null
                  ? `${usage.totals.database_gb.toFixed(2)} GB`
                  : "—",
              ],
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
                  <th className="px-4 py-3 text-right">Est. storage</th>
                  <th className="px-4 py-3 text-right">Warehouse rows</th>
                  <th className="px-4 py-3 text-right">LLM calls</th>
                  <th className="px-4 py-3 text-right">Exports</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {usage.customers.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No usage recorded for this period yet.
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
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {formatMb(row.estimated_storage_mb)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {formatInt(row.warehouse_rows)}
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
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
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
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Neon storage</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-white">
                {health.storage.database_gb != null
                  ? `${health.storage.database_gb.toFixed(2)} GB`
                  : "—"}
              </p>
              {health.storage.tenant_table_gb != null ? (
                <p className="mt-1 text-xs text-slate-500">
                  Tenant tables ~{health.storage.tenant_table_gb.toFixed(2)} GB
                </p>
              ) : null}
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Alert status</p>
              <p className={`mt-2 text-2xl font-semibold capitalize ${alertStatusClass(health.alerts.status)}`}>
                {health.alerts.status}
              </p>
            </div>
            {[
              ["LLM calls (24h)", formatInt(health.last_24h.llm_calls)],
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

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
              <h2 className="mb-3 text-sm font-semibold text-white">Top Neon tables</h2>
              {health.storage.top_tables.length === 0 ? (
                <p className="text-sm text-slate-500">No storage snapshot yet.</p>
              ) : (
                <ul className="divide-y divide-white/5 text-sm">
                  {health.storage.top_tables.map((row) => (
                    <li
                      key={row.table}
                      className="flex justify-between py-2 text-slate-300"
                    >
                      <span>{row.table}</span>
                      <span className="tabular-nums text-slate-400">{row.size_mb.toFixed(1)} MB</span>
                    </li>
                  ))}
                </ul>
              )}
              {health.storage.captured_at ? (
                <p className="mt-3 text-xs text-slate-500">
                  Snapshot: {health.storage.captured_at}
                </p>
              ) : null}
            </div>

            <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
              <h2 className="mb-3 text-sm font-semibold text-white">Storage trend (90d)</h2>
              {health.storage.history.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Trend builds as daily snapshots accumulate.
                </p>
              ) : (
                <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-slate-300">
                  {health.storage.history.map((point) => (
                    <li key={point.captured_at} className="flex justify-between">
                      <span className="text-slate-500">{point.captured_at.slice(0, 10)}</span>
                      <span className="tabular-nums">
                        {point.database_gb != null ? `${point.database_gb.toFixed(2)} GB` : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {health.alerts.checks.length > 0 ? (
            <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
              <h2 className="mb-3 text-sm font-semibold text-white">Latest health check</h2>
              <ul className="divide-y divide-white/5 text-sm">
                {health.alerts.checks.map((check) => (
                  <li key={check.name} className="flex flex-wrap items-center gap-3 py-2">
                    <span className={check.ok ? "text-teal-300" : "text-rose-300"}>
                      {check.ok ? "OK" : "FAIL"}
                    </span>
                    <span className="text-white">{check.name}</span>
                    {check.detail ? (
                      <span className="text-slate-500">{check.detail}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

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
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">Recent events</h2>
            {health.recent_events.length === 0 ? (
              <p className="text-sm text-slate-500">No recent events.</p>
            ) : (
              <ul className="divide-y divide-white/5 text-sm text-slate-300">
                {health.recent_events.map((event, index) => (
                  <li key={`${event.created_at}-${index}`} className="py-2">
                    <span className="text-slate-400">{event.created_at}</span>
                    {" · "}
                    <span className="text-white">{event.event_type}</span>
                    {event.feature ? ` · ${event.feature}` : ""}
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
