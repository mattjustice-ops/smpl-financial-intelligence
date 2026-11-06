"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppSessionBanner } from "@/components/app/AppSessionBanner";
import { EmbeddedModuleChrome } from "@/components/app/EmbeddedModuleChrome";
import { PlatformModuleNavLinks } from "@/components/app/PlatformModuleNavLinks";
import { ReadinessPanel } from "@/components/workspace/ReadinessPanel";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { DEFAULT_USAGE_LIMITS } from "@/lib/entitlements/usage-limits";

type TabId = "usage" | "readiness";

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
  load_domains?: {
    as_of_period: string;
    domains: Array<{
      id: string;
      label: string;
      description: string;
      entity_types: string[];
      typical_systems: string[];
      status: string;
      source_system: string | null;
      last_source: string | null;
      last_entity_type: string | null;
      last_status: string | null;
      last_at: string | null;
      rows_imported: number;
      rows_rejected: number;
      api_batches: number;
      csv_batches: number;
    }>;
    supported_entity_types: string[];
  };
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

  useEffect(() => {
    void load();
  }, [load]);

  const limits = summary?.plan_limits ?? DEFAULT_USAGE_LIMITS;
  const usage = summary?.usage.usage;
  const usageLimits = summary?.usage.limits ?? limits;

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
    <div className="workspace-module space-y-6">
      <div className="workspace-module__header">
        <div>
          <p className="workspace-module__eyebrow">Workspace</p>
          <h1 className="workspace-module__title">
            {summary?.organization_name ?? "Your workspace"}
          </h1>
          <p className="workspace-module__sub">
            Usage, storage, and implementation readiness. Import, mapping, tie-out, and approval live in Close Engine.
          </p>
        </div>
        <div className="workspace-module__actions">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="workspace-module__btn"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <Link href="/app/board" className="workspace-module__link">
            Board Platform
          </Link>
        </div>
      </div>

      <div className="workspace-module__tabs">
        {(
          [
            ["usage", "Usage & storage"],
            ["readiness", "Readiness"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`workspace-module__tab${tab === id ? " is-active" : ""}`}
          >
            {label}
          </button>
        ))}
      </div>

      {summary?._fallback ? (
        <div className="workspace-module__alert workspace-module__alert--warn">
          {summary._fallback_reason ??
            "Usage is not available until the latest API is deployed."}
        </div>
      ) : null}

      {error ? (
        <div className="workspace-module__alert workspace-module__alert--error">{error}</div>
      ) : null}

      {loading && !summary ? <p className="workspace-module__muted">Loading workspace…</p> : null}

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
              <div key={label} className="workspace-module__card">
                <p className="workspace-module__card-label">{label}</p>
                <p className="workspace-module__card-value">{value}</p>
                {cap !== "—" ? (
                  <p className="mt-1 workspace-module__muted">Cap {cap}</p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {tab === "readiness" ? <ReadinessPanel organizationId={organizationId} /> : null}
    </div>
  );
}

export function WorkspaceShell() {
  return (
    <EmbeddedModuleChrome moduleTitle="Workspace" links={<PlatformModuleNavLinks />}>
      <div className="embedded-module__scroll">
        <div className="embedded-module__scroll-inner">
          <div className="mb-6">
            <AppSessionBanner />
          </div>
          <WorkspaceDashboard />
        </div>
      </div>
    </EmbeddedModuleChrome>
  );
}
