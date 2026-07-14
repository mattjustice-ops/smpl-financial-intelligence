"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, Fragment } from "react";

import { AppSessionBanner } from "@/components/app/AppSessionBanner";
import { CloseWorkflowPanel } from "@/components/workspace/CloseWorkflowPanel";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { DEFAULT_USAGE_LIMITS } from "@/lib/entitlements/usage-limits";

type TabId = "usage" | "data" | "ledger";

type DataTrace = {
  database: { host: string; database: string; provider: string };
  neon_query_hint: string;
  mrr_tables: Record<
    string,
    {
      table: string;
      exists: boolean;
      row_count: number;
      periods: string[];
      sample_rows: Array<Record<string, unknown>>;
    }
  >;
};

type BatchTrace = {
  database: { host: string; database: string; provider: string };
  neon_query_hint: string;
  destination: {
    destination_kind: string;
    destination_table: string | null;
    reporting_table: string | null;
    reporting_reads_this_table: boolean;
    replace_all_org_rows: boolean;
    warnings: string[];
  };
  destination_live: {
    table?: string;
    row_count: number;
    periods?: string[];
    sample_rows?: Array<Record<string, unknown>>;
  } | null;
  reporting_live: {
    table: string;
    row_count: number;
    periods: string[];
    sample_rows: Array<Record<string, unknown>>;
  } | null;
};

type IngestResponse = {
  batch?: { batch_id: string; rows_imported: number; rows_rejected: number };
  destination?: BatchTrace["destination"];
  destination_live?: BatchTrace["destination_live"];
  reporting_live?: BatchTrace["reporting_live"];
  database?: { host: string; database: string; provider: string };
  neon_query_hint?: string;
  warnings?: string[];
  detail?: unknown;
};

type WorkspaceSummary = {
  organization_name: string;
  plan_limits: typeof DEFAULT_USAGE_LIMITS;
  _fallback?: boolean;
  _fallback_reason?: string;
  usage: {
    month: string;
    usage: { ai_cost_usd: number; llm_calls: number; exports_complete: number };
    limits: typeof DEFAULT_USAGE_LIMITS;
  };
  storage: {
    warehouse_rows: number;
    estimated_storage_mb: number;
    captured_at?: string;
  };
  close_ledger: {
    ingest_by_source: Record<
      string,
      { batches: number; rows_staged: number; rows_imported: number; rows_rejected: number }
    >;
    event_totals: Record<string, number>;
    recent_row_errors: Array<{
      row_number: number | null;
      external_id: string | null;
      field_name: string | null;
      error_code: string | null;
      message: string | null;
      source: string;
      entity_type: string | null;
    }>;
    recent_batches: Array<{
      batch_id: string;
      source: string;
      status: string;
      entity_type: string | null;
      filename: string | null;
      rows_staged: number;
      rows_imported: number;
      rows_rejected: number;
      created_at: string;
    }>;
  };
  available_months: string[];
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
  if (value >= 1024) return `${(value / 1024).toFixed(2)} GB`;
  return `${value.toFixed(1)} MB`;
}

export function WorkspaceDashboard() {
  const { organizationId, isLoading: orgLoading } = useActiveOrganization();
  const [tab, setTab] = useState<TabId>("usage");
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadTrace, setUploadTrace] = useState<IngestResponse | null>(null);
  const [dataTrace, setDataTrace] = useState<DataTrace | null>(null);
  const [batchTraces, setBatchTraces] = useState<Record<string, BatchTrace>>({});
  const [traceBusy, setTraceBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!organizationId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/workspace/summary?organization_id=${encodeURIComponent(organizationId)}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        let detail = `Workspace API returned ${res.status}`;
        try {
          const body = (await res.json()) as { detail?: unknown; hint?: string };
          if (typeof body.detail === "string") detail = body.detail;
          if (body.hint) detail = `${detail} ${body.hint}`;
        } catch {
          // ignore
        }
        throw new Error(detail);
      }
      setSummary((await res.json()) as WorkspaceSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  const loadDataTrace = useCallback(async () => {
    if (!organizationId) return;
    try {
      const res = await fetch(
        `/api/workspace/data-trace?organization_id=${encodeURIComponent(organizationId)}`,
        { cache: "no-store" },
      );
      if (res.ok) {
        setDataTrace((await res.json()) as DataTrace);
      }
    } catch {
      // Trace is optional until API is deployed
    }
  }, [organizationId]);

  const loadBatchTrace = useCallback(
    async (batchId: string) => {
      if (!organizationId) return;
      setTraceBusy(batchId);
      try {
        const res = await fetch(
          `/api/workspace/batches/${encodeURIComponent(batchId)}/trace?organization_id=${encodeURIComponent(organizationId)}`,
          { cache: "no-store" },
        );
        if (res.ok) {
          const payload = (await res.json()) as BatchTrace;
          setBatchTraces((prev) => ({ ...prev, [batchId]: payload }));
        }
      } finally {
        setTraceBusy(null);
      }
    },
    [organizationId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (tab === "data") {
      void loadDataTrace();
    }
  }, [tab, loadDataTrace]);

  const limits = summary?.plan_limits ?? DEFAULT_USAGE_LIMITS;
  const usage = summary?.usage.usage;
  const usageLimits = summary?.usage.limits ?? limits;

  const onUpload = async () => {
    if (!organizationId || !uploadFile) return;
    setUploadBusy(true);
    setUploadMessage(null);
    setUploadTrace(null);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("organization_id", organizationId);
      fd.append("file", uploadFile);
      const res = await fetch("/api/ingest/csv", { method: "POST", body: fd });
      const body = (await res.json()) as IngestResponse;
      if (!res.ok) {
        throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
      }
      setUploadTrace(body);
      const dest = body.destination?.destination_table ?? "unknown";
      const periods = body.destination_live?.periods?.join(", ") ?? "—";
      setUploadMessage(
        `Import complete — ${body.batch?.rows_imported ?? 0} rows imported to ${dest}. Periods in table: ${periods}.`,
      );
      setUploadFile(null);
      await load();
      await loadDataTrace();
      setTab("data");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploadBusy(false);
    }
  };

  const ledgerRows = useMemo(() => summary?.close_ledger.recent_batches ?? [], [summary]);

  if (orgLoading) {
    return <p className="text-sm text-slate-400">Loading workspace…</p>;
  }

  if (!organizationId) {
    return (
      <p className="text-sm text-slate-400">
        No active workspace. Sign in and select an organization.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-400">Workspace</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">
            {summary?.organization_name ?? "Your workspace"}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Usage, data imports (CSV or API), and month-end close activity for your organization.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            href="/app/board"
            className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            Board Platform
          </Link>
        </div>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-1">
        {(
          [
            ["usage", "Usage & storage"],
            ["data", "Data imports"],
            ["ledger", "Close ledger"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium ${
              tab === id
                ? "border border-b-0 border-white/15 bg-slate-900 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {summary?._fallback ? (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {summary._fallback_reason ??
            "Close ledger and imports are not available until the latest API is deployed to Railway."}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {uploadMessage ? (
        <div className="rounded-xl border border-teal-400/30 bg-teal-400/10 px-4 py-3 text-sm text-teal-200">
          {uploadMessage}
          {uploadTrace?.warnings?.length ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-100">
              {uploadTrace.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          {uploadTrace?.database ? (
            <p className="mt-2 text-xs text-teal-300/80">
              DB: {uploadTrace.database.host} / {uploadTrace.database.database} ({uploadTrace.database.provider})
            </p>
          ) : null}
          {uploadTrace?.reporting_live ? (
            <p className="mt-1 text-xs text-teal-300/80">
              Reporting table {uploadTrace.reporting_live.table}: {uploadTrace.reporting_live.row_count} rows
              {uploadTrace.reporting_live.periods.length
                ? ` · periods ${uploadTrace.reporting_live.periods.join(", ")}`
                : ""}
            </p>
          ) : null}
        </div>
      ) : null}

      {loading && !summary ? <p className="text-sm text-slate-400">Loading workspace…</p> : null}

      {tab === "usage" && summary && usage ? (
        <section className="space-y-4">
          <p className="text-xs text-slate-500">
            Calendar month {summary.usage.month} · caps apply to AI exports and copilot
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["AI spend", formatUsd(usage.ai_cost_usd), formatUsd(usageLimits.ai_cost_usd_monthly ?? 10)],
              ["LLM calls", formatInt(usage.llm_calls), formatInt(usageLimits.llm_calls_monthly ?? 10)],
              ["Exports", formatInt(usage.exports_complete), formatInt(usageLimits.exports_monthly ?? 10)],
              ["Warehouse rows", formatInt(summary.storage.warehouse_rows), "—"],
              ["Est. storage", formatMb(summary.storage.estimated_storage_mb), "—"],
            ].map(([label, value, cap]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{value}</p>
                {cap !== "—" ? (
                  <p className="mt-1 text-xs text-slate-500">Cap {cap}</p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {tab === "data" && summary ? (
        <section className="space-y-6">
          {organizationId ? <CloseWorkflowPanel organizationId={organizationId} /> : null}
          <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
            <h2 className="text-sm font-medium text-white">Upload CSV</h2>
            <p className="mt-1 text-xs text-slate-500">
              Use exact SMPL template names (e.g. <code className="text-slate-400">Actual_MRR_Waterfall.csv</code>).
              Renamed files land in a separate table that reporting does not read.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                className="text-sm text-slate-300"
              />
              <button
                type="button"
                disabled={!uploadFile || uploadBusy}
                onClick={() => void onUpload()}
                className="rounded-lg border border-teal-400/30 bg-teal-400/10 px-3 py-2 text-sm text-teal-200 hover:bg-teal-400/20 disabled:opacity-50"
              >
                {uploadBusy ? "Uploading…" : "Upload & import"}
              </button>
            </div>
          </div>

          {dataTrace ? (
            <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
              <h2 className="text-sm font-medium text-white">Live database trace (MRR tables)</h2>
              <p className="mt-1 text-xs text-slate-500">
                Matches Railway prod DATABASE_URL — confirm this host in Neon SQL Editor:{" "}
                <span className="font-mono text-slate-400">{dataTrace.database.host}</span>
              </p>
              <div className="mt-4 overflow-x-auto rounded-lg border border-white/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-widest text-slate-400">
                    <tr>
                      <th className="px-4 py-2">Table</th>
                      <th className="px-4 py-2 text-right">Rows</th>
                      <th className="px-4 py-2">Periods</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    {Object.values(dataTrace.mrr_tables).map((t) => (
                      <tr key={t.table}>
                        <td className="px-4 py-2 font-mono text-xs">{t.table}</td>
                        <td className="px-4 py-2 text-right tabular-nums">{formatInt(t.row_count)}</td>
                        <td className="px-4 py-2 text-xs text-slate-400">
                          {t.periods.length ? t.periods.join(", ") : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 font-mono text-xs text-slate-500">{dataTrace.neon_query_hint}</p>
            </div>
          ) : null}

          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-widest text-slate-400">
                <tr>
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Entity</th>
                  <th className="px-4 py-3">File</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Staged</th>
                  <th className="px-4 py-3 text-right">Imported</th>
                  <th className="px-4 py-3 text-right">Rejected</th>
                  <th className="px-4 py-3">Trace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {ledgerRows.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                      No imports yet. Upload a CSV or send an API batch.
                    </td>
                  </tr>
                ) : (
                  ledgerRows.map((row) => {
                    const trace = batchTraces[row.batch_id];
                    return (
                      <Fragment key={row.batch_id}>
                        <tr>
                          <td className="px-4 py-3 text-xs text-slate-400">
                            {new Date(row.created_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3">{row.source}</td>
                          <td className="px-4 py-3 font-mono text-xs text-slate-400">
                            {row.entity_type ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-slate-400">{row.filename ?? "—"}</td>
                          <td className="px-4 py-3">{row.status}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{formatInt(row.rows_staged)}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{formatInt(row.rows_imported)}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{formatInt(row.rows_rejected)}</td>
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              disabled={traceBusy === row.batch_id}
                              onClick={() => void loadBatchTrace(row.batch_id)}
                              className="text-xs text-teal-300 hover:text-teal-200 disabled:opacity-50"
                            >
                              {traceBusy === row.batch_id ? "…" : trace ? "Refresh" : "Verify"}
                            </button>
                          </td>
                        </tr>
                        {trace ? (
                          <tr key={`${row.batch_id}-trace`}>
                            <td colSpan={9} className="bg-slate-950/50 px-4 py-3 text-xs text-slate-400">
                              <p>
                                Wrote to{" "}
                                <span className="font-mono text-slate-300">
                                  {trace.destination.destination_table ?? "?"}
                                </span>
                                {trace.destination.reporting_table &&
                                trace.destination.reporting_table !== trace.destination.destination_table ? (
                                  <>
                                    {" "}
                                    · reporting reads{" "}
                                    <span className="font-mono text-amber-200">
                                      {trace.destination.reporting_table}
                                    </span>{" "}
                                    ({trace.reporting_live?.row_count ?? 0} rows
                                    {trace.reporting_live?.periods?.length
                                      ? `: ${trace.reporting_live.periods.join(", ")}`
                                      : ""}
                                    )
                                  </>
                                ) : (
                                  <>
                                    {" "}
                                    · {trace.destination_live?.row_count ?? 0} rows live
                                    {trace.destination_live?.periods?.length
                                      ? ` · periods ${trace.destination_live.periods.join(", ")}`
                                      : ""}
                                  </>
                                )}
                              </p>
                              {trace.destination.warnings.map((w) => (
                                <p key={w} className="mt-1 text-amber-200">
                                  {w}
                                </p>
                              ))}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {tab === "ledger" && summary ? (
        <section className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(summary.close_ledger.ingest_by_source).map(([source, totals]) => (
              <div key={source} className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500">{source}</p>
                <p className="mt-2 text-sm text-slate-300">
                  {totals.batches} batches · {formatInt(totals.rows_imported)} imported ·{" "}
                  {formatInt(totals.rows_rejected)} rejected
                </p>
              </div>
            ))}
            {Object.entries(summary.close_ledger.event_totals).map(([eventType, count]) => (
              <div key={eventType} className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500">{eventType}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{formatInt(count)}</p>
              </div>
            ))}
          </div>

          <div>
            <h2 className="mb-3 text-sm font-medium text-white">Recent row errors</h2>
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-widest text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Entity</th>
                    <th className="px-4 py-3 text-right">Row</th>
                    <th className="px-4 py-3">External ID</th>
                    <th className="px-4 py-3">Field</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Message</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-200">
                  {summary.close_ledger.recent_row_errors.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                        No row errors in this period.
                      </td>
                    </tr>
                  ) : (
                    summary.close_ledger.recent_row_errors.map((row, idx) => (
                      <tr key={`${row.row_number}-${idx}`}>
                        <td className="px-4 py-3">{row.source}</td>
                        <td className="px-4 py-3 text-slate-400">{row.entity_type ?? "—"}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{row.row_number ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-400">{row.external_id ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-400">{row.field_name ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-400">{row.error_code ?? "—"}</td>
                        <td className="px-4 py-3 text-xs">{row.message ?? "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

export function WorkspaceShell() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <div className="mx-auto max-w-6xl px-6 py-10 md:py-14">
        <div className="mb-6 text-white [&_a]:text-slate-400">
          <AppSessionBanner />
        </div>
        <WorkspaceDashboard />
      </div>
    </main>
  );
}
