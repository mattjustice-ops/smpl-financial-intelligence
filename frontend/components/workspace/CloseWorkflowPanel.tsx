"use client";

import { useCallback, useEffect, useState } from "react";

type CloseWorkflowPayload = {
  as_of_period: string;
  workflow_state: string;
  customer_ladder: string;
  current_lock_version: number;
  ready_to_lock: boolean;
  blockers: string[];
  warnings: string[];
  freeze_status: string;
  certified_close: boolean;
  certification_timestamp: string | null;
  close_session_id: string;
  checklist?: {
    items: Array<{
      id: string;
      label: string;
      status: string;
      detail: string;
    }>;
  };
  load_receipts?: Array<{
    id: string;
    entity_type: string | null;
    status: string;
    rows_staged: number;
    rows_applied: number;
    rows_rejected: number;
    created_at: string | null;
  }>;
};

export function CloseWorkflowPanel({ organizationId }: { organizationId: string }) {
  const [data, setData] = useState<CloseWorkflowPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/close-workflow?organization_id=${encodeURIComponent(organizationId)}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        throw new Error(`Close workflow API returned ${res.status}`);
      }
      setData((await res.json()) as CloseWorkflowPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  const postAction = async (path: string) => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/close-workflow/${path}?organization_id=${encodeURIComponent(organizationId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
          cache: "no-store",
        },
      );
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = body?.detail;
        const blockers = detail?.blockers;
        const msg =
          (Array.isArray(blockers) && blockers.length
            ? blockers.join("; ")
            : detail?.message) ||
          detail?.message ||
          `Request failed (${res.status})`;
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  if (!data && !error) {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4 text-sm text-slate-400">
        Loading close workflow…
      </div>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Customer Close Workflow</h2>
          <p className="mt-1 text-xs text-slate-400">
            Period {data?.as_of_period ?? "—"} · {data?.customer_ladder ?? "—"}
          </p>
        </div>
        <div className="text-right text-xs text-slate-400">
          <div className="font-mono text-teal-300">{data?.workflow_state ?? "—"}</div>
          <div>Lock v{data?.current_lock_version ?? 0}</div>
        </div>
      </div>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}

      {data?.blockers?.length ? (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-100">
          <p className="font-medium">Blocking executive lock</p>
          <ul className="mt-1 list-disc pl-5 text-xs">
            {data.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {data?.checklist?.items?.length ? (
        <ul className="space-y-2 text-sm">
          {data.checklist.items.map((item) => (
            <li key={item.id} className="flex gap-2 text-slate-300">
              <span
                className={
                  item.status === "completed"
                    ? "text-teal-300"
                    : item.status === "blocking"
                      ? "text-rose-300"
                      : item.status === "warning"
                        ? "text-amber-300"
                        : "text-slate-500"
                }
              >
                {item.status === "completed"
                  ? "✓"
                  : item.status === "blocking"
                    ? "✗"
                    : item.status === "warning"
                      ? "!"
                      : "○"}
              </span>
              <span>
                <span className="text-white">{item.label}</span>
                <span className="block text-xs text-slate-500">{item.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {data?.certified_close ? (
        <div className="rounded-md border border-teal-500/30 bg-teal-500/10 p-3 text-sm text-teal-100">
          <p className="font-medium">Certified Close</p>
          <p className="mt-1 font-mono text-xs">
            Session {data.close_session_id.slice(0, 8)}… · Lock v{data.current_lock_version}
            {data.certification_timestamp
              ? ` · ${new Date(data.certification_timestamp).toLocaleString()}`
              : ""}
          </p>
          <p className="mt-1 text-xs text-teal-200/80">Freeze: {data.freeze_status}</p>
        </div>
      ) : null}

      {(data?.load_receipts?.length ?? 0) > 0 ? (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Recent load receipts
          </h3>
          <ul className="divide-y divide-white/5 text-xs text-slate-400">
            {data!.load_receipts!.slice(0, 5).map((r) => (
              <li key={r.id} className="flex flex-wrap gap-x-3 py-1.5">
                <span className="text-slate-300">{r.entity_type || "unknown"}</span>
                <span>
                  {r.rows_staged} staged → {r.rows_applied} applied
                  {r.rows_rejected ? ` · ${r.rows_rejected} rejected` : ""}
                </span>
                <span className="text-slate-600">{r.status}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !data?.ready_to_lock}
          onClick={() => void postAction("lock")}
          className="rounded-md border border-teal-500/40 bg-teal-500/10 px-3 py-1.5 text-xs text-teal-200 hover:bg-teal-500/20 disabled:opacity-40"
        >
          {busy ? "Working…" : "Lock close month"}
        </button>
        <button
          type="button"
          disabled={busy || (data?.current_lock_version ?? 0) < 1}
          onClick={() => {
            if (
              window.confirm(
                "Reopen for more loads? Prior decks stay tied to the previous lock version.",
              )
            ) {
              void postAction("reopen");
            }
          }}
          className="rounded-md border border-white/15 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 hover:border-amber-500/40 disabled:opacity-40"
        >
          Reopen
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void load()}
          className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-slate-400"
        >
          Refresh
        </button>
      </div>
    </section>
  );
}
