"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";

import { CsvUploadPanel } from "../../components/CsvUploadPanel";
import { getApiBase, getApiBaseDisplay } from "../../lib/apiBase";

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
  | { kind: "error"; message: string; hint?: string };

async function fetchHealthJson<T>(url: string, timeoutMs = 8000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
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
  }
}

export default function ProductAppPage() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const apiBase = getApiBase();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const apiJson = await fetchHealthJson<{ status?: string }>(`${apiBase}/health`, 5000);
        let dbLabel = "not checked";
        let dbWarning: string | undefined;
        try {
          const dbJson = await fetchHealthJson<{ status?: string; database?: string }>(
            `${apiBase}/health/db`,
            6000
          );
          dbLabel = dbJson.database ?? dbJson.status ?? "unknown";
        } catch (dbErr) {
          dbLabel = "unreachable";
          dbWarning =
            dbErr instanceof Error
              ? `${dbErr.message}. Start Postgres: docker compose up -d`
              : "Database check failed. Run docker compose up -d from the project root.";
        }

        if (!cancelled) {
          setHealth({
            kind: "ok",
            api: apiJson.status ?? "unknown",
            db: dbLabel,
            dbWarning,
          });
        }
      } catch (e) {
        const isTimeout = e instanceof Error && e.name === "AbortError";
        const message = isTimeout
          ? `Timed out reaching backend at ${apiBase}.`
          : e instanceof Error
            ? e.message
            : "Unknown error";
        const hint = isTimeout
          ? "In backend/: run .\\restart-api.ps1 -Port 8001 — open http://127.0.0.1:8001/health before loading the operating system."
          : undefined;
        if (!cancelled) setHealth({ kind: "error", message, hint });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const apiReady = health.kind === "ok" && health.api === "ok";

  return (
    <main className="os-app">
      <div className="os-workspace">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <Link href="/" style={{ fontSize: 13, color: "var(--muted)", textDecoration: "none" }}>
            ← SMPL.ai home
          </Link>
        </div>
        <details className="os-workspace-panel">
          <summary>Workspace · data upload &amp; API health</summary>
          <div style={{ marginTop: 12, display: "grid", gap: 12 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
              {getApiBaseDisplay()}
            </div>

            {health.kind === "loading" && <div style={{ fontSize: 13 }}>Checking API and database…</div>}

            {health.kind === "error" && (
              <div style={{ color: "var(--negative)", fontSize: 13, lineHeight: 1.6 }}>
                <div>Could not reach the backend: {health.message}</div>
                {health.hint && <div style={{ marginTop: 8, color: "var(--muted)" }}>{health.hint}</div>}
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

      {apiReady ? (
        <div className="os-workspace" style={{ paddingBottom: 32 }}>
          <ExecutiveFlowDashboard enabled />
        </div>
      ) : health.kind === "error" ? (
        <div className="os-workspace">
          <div className="os-shell" style={{ padding: 24, color: "var(--muted)", lineHeight: 1.6 }}>
            The operating system loads after the API is reachable. Start Postgres (<code>docker compose up -d</code>),
            then backend (<code>.\\restart-api.ps1 -Port 8001</code>), then frontend (<code>npm run dev</code>).
          </div>
        </div>
      ) : (
        <div className="os-workspace">
          <div className="os-shell" style={{ padding: 24, color: "var(--muted)" }}>
            Preparing operating intelligence…
          </div>
        </div>
      )}
    </main>
  );
}
