"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_USAGE_LIMITS,
  type PlanUsageLimits,
  type UsageLimitKey,
} from "@/lib/entitlements/usage-limits";

type TabId = "usage" | "health" | "readiness";

type CloseReadinessRow = {
  organization_id: string;
  organization_name: string | null;
  plan: string | null;
  as_of_period: string;
  close_session_id: string | null;
  close_session_status: string | null;
  validation_status: string;
  trust_label: string | null;
  validation_check_ids?: string[];
  prompt5_deck_runs_used?: number;
  prompt5_deck_runs_limit?: number;
  prompt5_deck_runs_remaining?: number | null;
  freeze_status: string;
  queue_status: {
    status: string;
    active_count: number;
    latest_kind: string | null;
    latest_status: string | null;
  };
  operational_confidence: string;
  close_ready_phase1: boolean;
  customer_ladder: string;
  as_of_timestamp: string | null;
  last_successful_refresh: string | null;
};

type CloseReadinessResponse = {
  as_of_period: string;
  generated_at: string;
  organizations_total: number;
  organizations_ready: number;
  organizations: CloseReadinessRow[];
};

type CustomerRow = {
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
  limits?: Partial<PlanUsageLimits>;
  percent_used?: Partial<Record<UsageLimitKey, number | null>>;
};

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
  plan_limits?: PlanUsageLimits;
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
  customers: CustomerRow[];
  limits_enabled?: boolean;
};

type WarehouseOrgHealth = {
  ok: boolean;
  status: "ready" | "incomplete" | "empty" | "error";
  organization_id: string;
  organization_name: string | null;
  plan: string | null;
  close_month: string | null;
  issues: string[];
  actual_mrr_row_count: number;
  actual_mrr_periods: string[];
  board_hydrate_ready: boolean;
  close_month_ending_arr?: number | null;
};

type WarehouseHealthSummary = {
  ok: boolean;
  organizations_total: number;
  organizations_ready: number;
  organizations_incomplete: number;
  organizations_empty: number;
  organizations_error: number;
  organizations: WarehouseOrgHealth[];
  failing: WarehouseOrgHealth[];
};

type PlatformHealthResponse = {
  generated_at: string;
  database: { ok: boolean; latency_ms: number | null };
  warehouse?: WarehouseHealthSummary;
  storage: {
    database_gb?: number;
    tenant_table_gb?: number;
    captured_at?: string;
    top_tables: Array<{ table: string; size_mb: number }>;
    history: Array<{ captured_at: string; database_gb?: number; tenant_table_gb?: number }>;
  };
  alerts: {
    status: string;
    stored_status?: string;
    last_check_at: string | null;
    checks: Array<{ name: string; ok: boolean; detail?: string; latency_ms?: number }>;
  };
  export_jobs: {
    active_count: number;
    queued?: number;
    running?: number;
    failed?: number;
    complete?: number;
    oldest_queued_seconds?: number | null;
    durable?: boolean;
    jobs: Array<{
      job_id: string;
      kind: string;
      status: string;
      message: string;
      organization_id: string | null;
      error: string | null;
      age_seconds: number;
      running_seconds: number | null;
      durable?: boolean;
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
  deploy_freeze?: {
    active: boolean;
    note?: string;
    until?: string | null;
  };
};

function warehouseStatusLabel(status: WarehouseOrgHealth["status"]): string {
  switch (status) {
    case "ready":
      return "Ready";
    case "incomplete":
      return "Incomplete";
    case "empty":
      return "No data";
    case "error":
      return "Error";
    default:
      return status;
  }
}

function warehouseStatusPill(status: WarehouseOrgHealth["status"]): string {
  switch (status) {
    case "ready":
      return "border-teal-400/40 bg-teal-400/10 text-teal-200";
    case "empty":
      return "border-amber-400/40 bg-amber-400/10 text-amber-200";
    default:
      return "border-rose-400/40 bg-rose-400/10 text-rose-200";
  }
}

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

function resolveUsageLimit(
  usage: CustomerUsageResponse,
  row: CustomerRow,
  key: UsageLimitKey,
): number {
  const fromRow = row.limits?.[key];
  if (fromRow != null) return fromRow;
  const fromApi = usage.plan_limits?.[key];
  if (fromApi != null) return fromApi;
  return DEFAULT_USAGE_LIMITS[key] ?? 0;
}

export function SmplOpsDashboard() {
  const [tab, setTab] = useState<TabId>("usage");
  const [usage, setUsage] = useState<CustomerUsageResponse | null>(null);
  const [health, setHealth] = useState<PlatformHealthResponse | null>(null);
  const [readiness, setReadiness] = useState<CloseReadinessResponse | null>(null);
  const [prewarmBusy, setPrewarmBusy] = useState(false);
  const [prewarmMsg, setPrewarmMsg] = useState<string | null>(null);
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

  const planLimits = useMemo(
    () => usage?.plan_limits ?? DEFAULT_USAGE_LIMITS,
    [usage?.plan_limits],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const readinessMonth =
        selectedMonth ||
        `${new Date().getUTCFullYear()}-${String(new Date().getUTCMonth() + 1).padStart(2, "0")}`;
      const [usageRes, healthRes, readinessRes] = await Promise.all([
        fetch(`/api/ops/customer-usage?${usageQuery}`, { cache: "no-store" }),
        fetch("/api/ops/platform-health", { cache: "no-store" }),
        fetch(
          `/api/ops/close-readiness?month=${encodeURIComponent(readinessMonth)}`,
          { cache: "no-store" },
        ),
      ]);
      if (!usageRes.ok) {
        throw new Error(`Customer usage API returned ${usageRes.status}`);
      }
      if (!healthRes.ok) {
        throw new Error(`Platform health API returned ${healthRes.status}`);
      }
      setUsage((await usageRes.json()) as CustomerUsageResponse);
      setHealth((await healthRes.json()) as PlatformHealthResponse);
      if (readinessRes.ok) {
        setReadiness((await readinessRes.json()) as CloseReadinessResponse);
      } else {
        setReadiness(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [usageQuery, selectedMonth]);

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

  const runPrewarm = async (dryRun: boolean) => {
    setPrewarmBusy(true);
    setPrewarmMsg(null);
    setError(null);
    try {
      const qs = new URLSearchParams({ dry_run: dryRun ? "true" : "false" });
      const res = await fetch(`/api/ops/prewarm-freeze?${qs}`, {
        method: "POST",
        cache: "no-store",
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `Prewarm API returned ${res.status}`);
      }
      const data = (await res.json()) as {
        total?: number;
        succeeded?: number;
        failed?: number;
        dry_run?: boolean;
      };
      setPrewarmMsg(
        `${data.dry_run ? "Dry run" : "Prewarm"}: ${data.succeeded ?? 0}/${data.total ?? 0} ok` +
          (data.failed ? `, ${data.failed} failed` : ""),
      );
      if (!dryRun) await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPrewarmBusy(false);
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
            Customer usage, platform health &amp; close readiness
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
            ["readiness", "Close readiness"],
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

      {health?.deploy_freeze?.active ? (
        <div className="mb-6 rounded-xl border border-amber-400/40 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          <p className="font-semibold text-amber-200">Close-week deploy freeze</p>
          <p className="mt-1 text-amber-100/90">
            {health.deploy_freeze.note ||
              "Avoid non-critical production deploys during close week."}
          </p>
          {health.deploy_freeze.until ? (
            <p className="mt-1 text-xs text-amber-200/70">Until: {health.deploy_freeze.until}</p>
          ) : null}
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
            <p className="text-xs text-slate-500">
              Monthly caps (all plans): {formatUsd(planLimits.ai_cost_usd_monthly ?? 10)} AI ·{" "}
              {formatInt(planLimits.llm_calls_monthly ?? 10)} LLM calls ·{" "}
              {formatInt(planLimits.exports_monthly ?? 10)} exports
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
            {[
              ["AI spend", formatUsd(usage.totals.ai_cost_usd)],
              ["AI cap", formatUsd(planLimits.ai_cost_usd_monthly ?? 10)],
              ["LLM calls", formatInt(usage.totals.llm_calls)],
              ["LLM cap", formatInt(planLimits.llm_calls_monthly ?? 10)],
              ["Exports", formatInt(usage.totals.exports_complete)],
              ["Export cap", formatInt(planLimits.exports_monthly ?? 10)],
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

          <div className="grid gap-4 sm:grid-cols-2">
            {[
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
                  <th className="px-4 py-3 text-right">Cap</th>
                  <th className="px-4 py-3 text-right">Est. storage</th>
                  <th className="px-4 py-3 text-right">Warehouse rows</th>
                  <th className="px-4 py-3 text-right">LLM calls</th>
                  <th className="px-4 py-3 text-right">Cap</th>
                  <th className="px-4 py-3 text-right">Exports</th>
                  <th className="px-4 py-3 text-right">Cap</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {usage.customers.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                      No usage recorded for this period yet.
                    </td>
                  </tr>
                ) : (
                  usage.customers.map((row) => {
                    const aiCap = resolveUsageLimit(usage, row, "ai_cost_usd_monthly");
                    const llmCap = resolveUsageLimit(usage, row, "llm_calls_monthly");
                    const exportCap = resolveUsageLimit(usage, row, "exports_monthly");

                    return (
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
                          {formatUsd(aiCap)}
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
                        <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                          {formatInt(llmCap)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {formatInt(row.exports_complete)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                          {formatInt(exportCap)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {tab === "health" && health ? (
        <section className="space-y-6">
          {health.warehouse && health.warehouse.failing.length > 0 ? (
            <div className="rounded-xl border border-rose-400/40 bg-rose-400/10 px-4 py-4 text-sm text-rose-100">
              <p className="font-medium text-rose-200">
                {health.warehouse.failing.length} customer warehouse
                {health.warehouse.failing.length === 1 ? "" : "s"} cannot hydrate /app/board
              </p>
              <ul className="mt-3 space-y-3">
                {health.warehouse.failing.map((org) => (
                  <li key={org.organization_id}>
                    <p className="font-medium text-rose-100">
                      {org.organization_name ?? org.organization_id}
                      {org.close_month ? ` · close ${org.close_month}` : ""}
                    </p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-rose-100/90">
                      {org.issues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Customer warehouses</p>
              <p className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusPill(health.warehouse?.ok ?? false)}`}
                >
                  {health.warehouse
                    ? `${health.warehouse.organizations_ready}/${health.warehouse.organizations_total} ready`
                    : "—"}
                </span>
              </p>
              {health.warehouse ? (
                <p className="mt-2 text-xs text-slate-500">
                  {health.warehouse.organizations_incomplete} incomplete ·{" "}
                  {health.warehouse.organizations_empty} no data yet
                </p>
              ) : null}
            </div>
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
              {health.alerts.stored_status &&
              health.alerts.stored_status !== health.alerts.status ? (
                <p className="mt-1 text-xs text-slate-500">
                  Scheduled check: {health.alerts.stored_status} · live warehouse included
                </p>
              ) : null}
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

          {health.warehouse && health.warehouse.organizations.length > 0 ? (
            <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
              <h2 className="mb-3 text-sm font-semibold text-white">Customer warehouse health</h2>
              <p className="mb-4 text-xs text-slate-500">
                Each active customer org is checked against the same rules as /app/board live hydration.
              </p>
              <div className="overflow-x-auto rounded-lg border border-white/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-widest text-slate-400">
                    <tr>
                      <th className="px-4 py-3">Organization</th>
                      <th className="px-4 py-3">Plan</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Close month</th>
                      <th className="px-4 py-3 text-right">MRR periods</th>
                      <th className="px-4 py-3">Periods loaded</th>
                      <th className="px-4 py-3">Issues</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    {health.warehouse.organizations.map((org) => (
                      <tr key={org.organization_id}>
                        <td className="px-4 py-3">
                          <div className="font-medium text-white">{org.organization_name ?? "—"}</div>
                          <div className="text-xs text-slate-500">{org.organization_id}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{org.plan ?? "—"}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-xs font-medium ${warehouseStatusPill(org.status)}`}
                          >
                            {warehouseStatusLabel(org.status)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{org.close_month ?? "—"}</td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {formatInt(org.actual_mrr_row_count)}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {org.actual_mrr_periods.length
                            ? org.actual_mrr_periods.join(", ")
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {org.issues.length ? org.issues.join(" · ") : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

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
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-white">
                Export queue {health.export_jobs.durable ? "(durable)" : "(in-memory fallback)"}
              </h2>
              <span className="text-xs text-slate-500">
                {health.export_jobs.queued ?? 0} queued · {health.export_jobs.running ?? 0} running
                {(health.export_jobs.failed ?? 0) > 0
                  ? ` · ${health.export_jobs.failed} failed`
                  : ""}
              </span>
            </div>
            {health.export_jobs.oldest_queued_seconds != null ? (
              <p className="mb-2 text-xs text-amber-300/90">
                Oldest queued wait: {health.export_jobs.oldest_queued_seconds}s
              </p>
            ) : null}
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
                    {job.error ? (
                      <span className="w-full text-xs text-rose-300">{job.error}</span>
                    ) : null}
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

      {tab === "readiness" ? (
        <section className="space-y-6">
          <div className="flex flex-wrap items-end gap-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <label className="text-sm text-slate-400">
              Close month
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
            {readiness ? (
              <p className="text-sm text-slate-400">
                {readiness.organizations_ready}/{readiness.organizations_total} Close Ready
                (Phase 1) · as of {formatMonthLabel(readiness.as_of_period)}
              </p>
            ) : (
              <p className="text-sm text-slate-500">
                Close readiness requires migration <code>close_001</code> on the API database.
              </p>
            )}
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={prewarmBusy}
                onClick={() => void runPrewarm(true)}
                className="rounded-md border border-white/15 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 hover:border-teal-500/40 disabled:opacity-50"
              >
                Dry-run prewarm
              </button>
              <button
                type="button"
                disabled={prewarmBusy}
                onClick={() => void runPrewarm(false)}
                className="rounded-md border border-teal-500/40 bg-teal-500/10 px-3 py-1.5 text-xs text-teal-200 hover:bg-teal-500/20 disabled:opacity-50"
              >
                {prewarmBusy ? "Prewarming…" : "Prewarm freezes"}
              </button>
            </div>
            {prewarmMsg ? (
              <p className="w-full text-xs text-teal-300/90">{prewarmMsg}</p>
            ) : null}
          </div>

          {readiness ? (
            <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/40">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Organization</th>
                    <th className="px-4 py-3 font-medium">Session</th>
                    <th className="px-4 py-3 font-medium">Validation</th>
                    <th className="px-4 py-3 font-medium">Checks</th>
                    <th className="px-4 py-3 font-medium">Freeze</th>
                    <th className="px-4 py-3 font-medium">P5 decks</th>
                    <th className="px-4 py-3 font-medium">Queue</th>
                    <th className="px-4 py-3 font-medium">Ready</th>
                    <th className="px-4 py-3 font-medium">Ladder</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {readiness.organizations.map((row) => (
                    <tr key={row.organization_id} className="text-slate-300">
                      <td className="px-4 py-3">
                        <div className="font-medium text-white">
                          {row.organization_name || row.organization_id}
                        </div>
                        {row.plan ? (
                          <div className="text-xs text-slate-500">{row.plan}</div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400">
                        {row.close_session_id ? (
                          <button
                            type="button"
                            className="hover:text-teal-300"
                            title="Copy close session ID"
                            onClick={() => {
                              void navigator.clipboard.writeText(row.close_session_id || "");
                            }}
                          >
                            {row.close_session_id.slice(0, 8)}…
                          </button>
                        ) : (
                          "—"
                        )}
                        {row.close_session_status ? (
                          <div className="mt-1 text-[11px] text-slate-500">
                            {row.close_session_status}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            row.validation_status === "pass"
                              ? "text-teal-300"
                              : row.validation_status === "warning"
                                ? "text-amber-300"
                                : row.validation_status === "fail"
                                  ? "text-rose-300"
                                  : "text-slate-500"
                          }
                        >
                          {row.trust_label || row.validation_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[11px] text-slate-500">
                        {(row.validation_check_ids?.length ?? 0) > 0
                          ? `${row.validation_check_ids!.length} ids`
                          : "—"}
                        {(row.validation_check_ids?.length ?? 0) > 0 ? (
                          <div
                            className="mt-1 max-w-[10rem] truncate font-mono text-[10px] text-slate-600"
                            title={row.validation_check_ids!.join(", ")}
                          >
                            {row.validation_check_ids!.slice(0, 2).join(", ")}
                            {(row.validation_check_ids!.length ?? 0) > 2 ? "…" : ""}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            row.freeze_status === "COMPLETE"
                              ? "text-teal-300"
                              : row.freeze_status === "STALE"
                                ? "text-amber-300"
                                : "text-slate-500"
                          }
                        >
                          {row.freeze_status}
                        </span>
                        {row.as_of_timestamp ? (
                          <div className="mt-1 text-[11px] text-slate-500">
                            {new Date(row.as_of_timestamp).toLocaleString()}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400">
                        {row.prompt5_deck_runs_remaining == null
                          ? `${row.prompt5_deck_runs_used ?? 0} used`
                          : `${row.prompt5_deck_runs_remaining} left`}
                        <div className="mt-1 text-[11px] text-slate-600">
                          {row.prompt5_deck_runs_used ?? 0}/{row.prompt5_deck_runs_limit ?? "—"}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {row.queue_status.status}
                        {row.queue_status.latest_kind
                          ? ` · ${row.queue_status.latest_kind}`
                          : ""}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            row.close_ready_phase1 ? "text-teal-300" : "text-slate-500"
                          }
                        >
                          {row.close_ready_phase1 ? "Phase 1 ready" : "Not ready"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{row.customer_ladder}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
