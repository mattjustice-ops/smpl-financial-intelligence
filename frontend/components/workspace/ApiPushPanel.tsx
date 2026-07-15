"use client";

import { useMemo, useState } from "react";

type LoadDomain = {
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
};

type LoadDomainsPayload = {
  as_of_period: string;
  domains: LoadDomain[];
  supported_entity_types: string[];
};

function statusTone(status: string): string {
  if (status === "loaded") return "text-teal-300";
  if (status === "partial") return "text-amber-300";
  if (status === "failed") return "text-rose-300";
  if (status === "in_progress") return "text-sky-300";
  return "text-slate-500";
}

function statusLabel(status: string): string {
  if (status === "loaded") return "Loaded";
  if (status === "partial") return "Partial — row errors";
  if (status === "failed") return "Failed";
  if (status === "in_progress") return "In progress";
  return "Not loaded";
}

export function ApiPushPanel({
  organizationId,
  loadDomains,
  onPushed,
}: {
  organizationId: string;
  loadDomains: LoadDomainsPayload | null | undefined;
  onPushed: () => Promise<void>;
}) {
  const domains = loadDomains?.domains ?? [];
  const [domainId, setDomainId] = useState(domains[0]?.id ?? "crm");
  const selectedDomain = useMemo(
    () => domains.find((d) => d.id === domainId) ?? domains[0],
    [domains, domainId],
  );
  const [entityType, setEntityType] = useState(selectedDomain?.entity_types[0] ?? "opportunities");
  const [sourceSystem, setSourceSystem] = useState(selectedDomain?.typical_systems[0] ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDomainChange = (id: string) => {
    setDomainId(id);
    const next = domains.find((d) => d.id === id);
    if (next) {
      setEntityType(next.entity_types[0] ?? "");
      setSourceSystem(next.typical_systems[0] ?? "");
    }
  };

  const pushData = async () => {
    if (!file || !entityType) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      const records = Array.isArray(parsed)
        ? parsed
        : parsed && typeof parsed === "object" && Array.isArray((parsed as { records?: unknown }).records)
          ? (parsed as { records: Record<string, unknown>[] }).records
          : null;
      if (!records?.length) {
        throw new Error("JSON must be an array of records, or { \"records\": [ ... ] }");
      }
      const res = await fetch(
        `/api/ingest/batches?organization_id=${encodeURIComponent(organizationId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            entity_type: entityType,
            records,
            source_system: sourceSystem || undefined,
          }),
        },
      );
      const body = (await res.json()) as {
        detail?: unknown;
        load_receipt?: { rows_staged: number; rows_applied: number; rows_rejected: number };
        batch?: { rows_imported?: number; rows_rejected?: number; status?: string };
      };
      if (!res.ok) {
        throw new Error(
          typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body),
        );
      }
      const applied = body.load_receipt?.rows_applied ?? body.batch?.rows_imported ?? 0;
      const rejected = body.load_receipt?.rows_rejected ?? body.batch?.rows_rejected ?? 0;
      setMessage(
        `Push complete from ${sourceSystem || "API"} → ${entityType}: ${applied} applied` +
          (rejected ? `, ${rejected} rejected` : "") +
          ".",
      );
      setFile(null);
      await onPushed();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
      <div>
        <h2 className="text-sm font-medium text-white">API / system push</h2>
        <p className="mt-1 text-xs text-slate-500">
          Load data from your systems when <em>you</em> are ready — Salesforce, NetSuite, Stripe,
          HRIS, etc. Same staging / applied / rejected checks as CSV. Integrators can also call{" "}
          <code className="text-slate-400">POST /api/v1/ingest/batches</code> directly; this Push
          control is for discretionary loads from the workspace.
        </p>
        {loadDomains?.as_of_period ? (
          <p className="mt-1 text-xs text-slate-600">Close period {loadDomains.as_of_period}</p>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {domains.map((domain) => (
          <button
            key={domain.id}
            type="button"
            onClick={() => onDomainChange(domain.id)}
            className={`rounded-lg border p-3 text-left transition ${
              domainId === domain.id
                ? "border-teal-500/50 bg-teal-500/10"
                : "border-white/10 bg-slate-950/40 hover:border-white/20"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-white">{domain.label}</p>
              <span className={`text-[11px] font-medium ${statusTone(domain.status)}`}>
                {statusLabel(domain.status)}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">{domain.description}</p>
            <p className="mt-2 text-[11px] text-slate-500">
              {domain.source_system || domain.typical_systems.join(" · ")}
            </p>
            <p className="mt-1 font-mono text-[11px] text-slate-600">
              {domain.rows_imported} applied
              {domain.rows_rejected ? ` · ${domain.rows_rejected} rejected` : ""}
              {domain.api_batches || domain.csv_batches
                ? ` · ${domain.api_batches} api / ${domain.csv_batches} csv`
                : ""}
            </p>
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-white/10 bg-slate-950/50 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Push data now
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Choose the system and dataset, then upload a JSON array of records exported from that
          system (or sent by your middleware). You decide when to push — we do not schedule this.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-xs text-slate-400">
            Domain
            <select
              value={domainId}
              onChange={(e) => onDomainChange(e.target.value)}
              className="mt-1 w-full rounded-md border border-white/15 bg-slate-950 px-2 py-1.5 text-sm text-white"
            >
              {domains.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Dataset (entity)
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="mt-1 w-full rounded-md border border-white/15 bg-slate-950 px-2 py-1.5 text-sm text-white"
            >
              {(selectedDomain?.entity_types ?? []).map((entity) => (
                <option key={entity} value={entity}>
                  {entity}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Source system
            <input
              value={sourceSystem}
              onChange={(e) => setSourceSystem(e.target.value)}
              list={`systems-${domainId}`}
              placeholder="e.g. Salesforce"
              className="mt-1 w-full rounded-md border border-white/15 bg-slate-950 px-2 py-1.5 text-sm text-white"
            />
            <datalist id={`systems-${domainId}`}>
              {(selectedDomain?.typical_systems ?? []).map((sys) => (
                <option key={sys} value={sys} />
              ))}
            </datalist>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".json,application/json"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-slate-300"
          />
          <button
            type="button"
            disabled={!file || busy || !entityType}
            onClick={() => void pushData()}
            className="rounded-lg border border-teal-400/30 bg-teal-400/10 px-3 py-2 text-sm text-teal-200 hover:bg-teal-400/20 disabled:opacity-50"
          >
            {busy ? "Pushing…" : "Push data"}
          </button>
        </div>
        {message ? <p className="mt-3 text-sm text-teal-200">{message}</p> : null}
        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      </div>
    </div>
  );
}
