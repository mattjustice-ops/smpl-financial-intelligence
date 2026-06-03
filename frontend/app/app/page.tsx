"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";

import { CsvUploadPanel } from "../../components/CsvUploadPanel";
import { getApiBaseDisplay } from "../../lib/apiBase";

const ExecutiveFlowDashboard = dynamic(
  () =>
    import("../../components/ExecutiveFlowDashboard").then((mod) => ({
      default: mod.ExecutiveFlowDashboard,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="os-shell" style={{ padding: 24, color: "var(--muted)" }}>
        Loading CFO operating system…
      </div>
    ),
  }
);

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; api: string; db: string; dbWarning?: string }
  | { kind: "error"; message: string };

async function fetchHealthJson<T>(url: string, signal: AbortSignal, timeoutMs = 4000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal.addEventListener("abort", onAbort);
  try {
    const res = await fetch(`${url}${url.includes("?") ? "&" : "?"}_=${Date.now()}`, {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache" },
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`${url} returned ${res.status}`);
    }
    return (await res.json()) as T;
  } finally {
    window.clearTimeout(timeout);
    signal.removeEventListener("abort", onAbort);
  }
}

export default function ProductAppPage() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const abort = new AbortController();

    async function load() {
      try {
        const apiJson = await fetchHealthJson<{ status?: string }>("/health", abort.signal, 4000);
        let dbLabel = "not checked";
        let dbWarning: string | undefined;
        try {
          const dbJson = await fetchHealthJson<{ status?: string; database?: string }>(
            "/health/db",
            abort.signal,
            4000
          );
          dbLabel = dbJson.database ?? dbJson.status ?? "connected";
        } catch {
          dbLabel = "unreachable";
          dbWarning = "Start Postgres: docker compose up -d. CSV upload requires the database.";
        }
        if (!abort.signal.aborted) {
          setHealth({
            kind: "ok",
            api: apiJson.status ?? "ok",
            db: dbLabel,
            dbWarning,
          });
        }
      } catch (e) {
        if (abort.signal.aborted) return;
        const message =
          e instanceof Error && e.name === "AbortError"
            ? "Health check timed out."
            : e instanceof Error
              ? e.message
              : "Unknown error";
        setHealth({ kind: "error", message });
      }
    }

    load();
    return () => abort.abort();
  }, []);

  return (
    <main className="os-app">
      <div className="os-workspace">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <Link href="/" style={{ fontSize: 13, color: "var(--muted)", textDecoration: "none" }}>
            ← SMPL.ai home
          </Link>
        </div>
        <details className="os-workspace-panel" open>
          <summary>Workspace · data upload &amp; API health</summary>
          <div style={{ marginTop: 12, display: "grid", gap: 12 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
              {getApiBaseDisplay()}
            </div>

            {health.kind === "loading" && (
              <div style={{ fontSize: 13 }}>Checking API and database (via Next.js proxy)…</div>
            )}

            {health.kind === "error" && (
              <div style={{ color: "var(--negative)", fontSize: 13, lineHeight: 1.6 }}>
                Health check failed: {health.message}. The dashboard still loads below — use CLI CSV load if
                upload fails. Confirm http://127.0.0.1:8001/health in your browser, then restart{" "}
                <code>npm run dev</code>.
              </div>
            )}

            {health.kind === "ok" && (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
                <li>
                  <strong>/health</strong>: {health.api}
                </li>
                <li>
                  <strong>/health/db</strong>: {health.db}
                  {health.dbWarning && (
                    <span style={{ display: "block", fontSize: 12, color: "var(--watch)" }}>{health.dbWarning}</span>
                  )}
                </li>
              </ul>
            )}

            <CsvUploadPanel />
          </div>
        </details>
      </div>

      <div className="os-workspace" style={{ paddingBottom: 32 }}>
        <ExecutiveFlowDashboard enabled />
      </div>
    </main>
  );
}
