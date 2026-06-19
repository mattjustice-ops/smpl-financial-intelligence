"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";
import { fetchJson } from "@/lib/fetchJson";

type ValidationCheck = {
  validation_name: string;
  status: "pass" | "warning" | "fail";
  period: string;
  scenario: string;
  variance?: string | number | null;
};

type BoardPayload = {
  meta: {
    organization_name: string;
    close_month: string;
    start_period: string;
    end_period: string;
    active_forecast_version_name: string | null;
  };
  executive: {
    kpis?: Array<{ label: string; value: string | number; delta?: string }>;
    scenario?: string;
  };
  validation: {
    status: string;
    failed_count: number;
    warning_count: number;
    checks: ValidationCheck[];
  };
  time_series: {
    periods?: string[];
    Actual?: Record<string, Record<string, number | null>>;
    Forecast?: Record<string, Record<string, number | null>>;
  };
  commentary: Record<string, Record<string, string>>;
};

const TABS = [
  { id: "executive", label: "Executive Summary" },
  { id: "arr", label: "ARR Waterfall" },
  { id: "revenue", label: "Revenue & ARR" },
  { id: "cash", label: "Cash Forecast" },
  { id: "statements", label: "3-Statement" },
  { id: "copilot", label: "SMPL Copilot" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function fmtMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function BoardPlatformApp() {
  const { organizationId, isLoading: orgLoading } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const [tab, setTab] = useState<TabId>("executive");
  const [payload, setPayload] = useState<BoardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copilotQ, setCopilotQ] = useState("");
  const [copilotA, setCopilotA] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  const canView = hasModule("board_export");
  const canAi = hasModule("ai_commentary");

  const loadPayload = useCallback(async () => {
    if (!organizationId || !canView) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<BoardPayload>(
        `/api/v1/board-platform/payload?organization_id=${organizationId}`,
        undefined,
        120000,
      );
      setPayload(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load board platform.");
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [organizationId, canView]);

  useEffect(() => {
    void loadPayload();
  }, [loadPayload]);

  const closeLabel = useMemo(() => {
    if (!payload) return "";
    const [y, m] = payload.meta.close_month.split("-");
    const dt = new Date(Number(y), Number(m) - 1, 1);
    return dt.toLocaleString("en-US", { month: "long", year: "numeric" });
  }, [payload]);

  async function regenerateCommentary() {
    if (!organizationId || !canAi) return;
    setRegenerating(true);
    try {
      const res = await fetchJson<{ commentary: Record<string, string> }>(
        `/api/v1/board-platform/commentary/regenerate?organization_id=${organizationId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slide_key: tab === "copilot" ? "executive" : tab }),
        },
      );
      setPayload((prev) =>
        prev
          ? {
              ...prev,
              commentary: { ...prev.commentary, [tab === "copilot" ? "executive" : tab]: res.commentary },
            }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Commentary regeneration failed.");
    } finally {
      setRegenerating(false);
    }
  }

  async function askCopilot() {
    if (!organizationId || !copilotQ.trim()) return;
    setCopilotA(null);
    try {
      const res = await fetchJson<{ answer: string }>(
        `/api/v1/board-platform/copilot?organization_id=${organizationId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: copilotQ.trim() }),
        },
      );
      setCopilotA(res.answer);
    } catch (e) {
      setCopilotA(e instanceof Error ? e.message : "Copilot unavailable.");
    }
  }

  function exportBoard(format: "pptx" | "excel") {
    if (!organizationId || !payload) return;
    const params = new URLSearchParams({
      organization_id: organizationId,
      scenario: "Combined",
      start_period: payload.meta.start_period,
      end_period: payload.meta.end_period,
      as_of_period: payload.meta.close_month,
      block_on_failure: "true",
      use_ai: canAi ? "true" : "false",
    });
    const path =
      format === "pptx"
        ? `/api/v1/export/board-presentation.pptx?${params}`
        : `/api/v1/export/management-review.xlsx?${params}`;
    window.open(path, "_blank", "noopener,noreferrer");
  }

  if (orgLoading) {
    return <div className="board-shell">Loading session…</div>;
  }

  if (!canView) {
    return (
      <div className="board-shell">
        <h1>Board Platform</h1>
        <p>Board Platform requires the board_export entitlement ({planLabel} plan).</p>
        <Link href="/app">Back to operating system</Link>
      </div>
    );
  }

  const commentary = payload?.commentary[tab === "copilot" ? "executive" : tab];

  return (
    <div className="board-shell">
      <header className="board-topbar">
        <div>
          <div className="board-logo">
            SMPL <span>· Board Platform</span>
          </div>
          <div className="board-sub">
            {payload?.meta.organization_name ?? "—"} · {closeLabel || "Live warehouse"} ·{" "}
            {payload?.meta.active_forecast_version_name
              ? `Forecast: ${payload.meta.active_forecast_version_name}`
              : "No active final forecast"}
          </div>
        </div>
        <div className="board-actions">
          <Link href="/forecast-engine" className="board-btn">
            Forecast Engine
          </Link>
          <Link href="/app" className="board-btn">
            Operating OS
          </Link>
          <button type="button" className="board-btn" onClick={() => exportBoard("pptx")} disabled={!payload}>
            Export PPTX
          </button>
          <button type="button" className="board-btn" onClick={() => exportBoard("excel")} disabled={!payload}>
            Export Excel
          </button>
        </div>
      </header>

      <nav className="board-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`board-nav-btn${tab === t.id ? " active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {loading && <div className="board-panel">Loading live board data…</div>}
      {error && (
        <div className="board-panel board-error">
          <strong>Board blocked — validation or load error</strong>
          <pre>{error}</pre>
          <button type="button" className="board-btn" onClick={() => void loadPayload()}>
            Retry
          </button>
        </div>
      )}

      {payload && !loading && (
        <>
          {payload.validation.failed_count > 0 || payload.validation.warning_count > 0 ? (
            <div className="board-panel board-error">
              Validation {payload.validation.status}: {payload.validation.failed_count} failed,{" "}
              {payload.validation.warning_count} warnings. Resolve before export.
            </div>
          ) : null}

          <section className="board-panel">
            {tab === "executive" && (
              <>
                <h2>Executive Summary</h2>
                <div className="board-kpi-strip">
                  {(payload.executive.kpis ?? []).slice(0, 5).map((kpi) => (
                    <div key={kpi.label} className="board-kpi">
                      <div className="board-kpi-lbl">{kpi.label}</div>
                      <div className="board-kpi-val">{kpi.value}</div>
                      {kpi.delta ? <div className="board-kpi-delta">{kpi.delta}</div> : null}
                    </div>
                  ))}
                </div>
              </>
            )}

            {tab === "arr" && <h2>ARR Waterfall — live Combined scenario</h2>}
            {tab === "revenue" && <h2>Revenue & ARR</h2>}
            {tab === "cash" && <h2>Cash Forecast & Liquidity</h2>}
            {tab === "statements" && <h2>3-Statement View</h2>}

            {tab !== "copilot" && (
              <div className="board-ts-grid">
                {(payload.time_series.periods ?? []).map((period) => {
                  const isFc = period > payload.meta.close_month;
                  const row =
                    (isFc ? payload.time_series.Forecast : payload.time_series.Actual)?.[period] ?? {};
                  return (
                    <div key={period} className="board-ts-card">
                      <div className="board-ts-period">
                        {period} · {isFc ? "Forecast" : "Actual"}
                      </div>
                      <div>Revenue {fmtMoney(row.revenue ?? null)}</div>
                      <div>EBITDA: {fmtMoney(row.ebitda ?? null)}</div>
                    </div>
                  );
                })}
              </div>
            )}

            {tab === "copilot" && (
              <div className="board-copilot">
                <p>Ask SMPL Copilot — answers grounded in live warehouse metrics.</p>
                <textarea
                  value={copilotQ}
                  onChange={(e) => setCopilotQ(e.target.value)}
                  rows={3}
                  placeholder="How is H2 ARR tracking vs budget?"
                />
                <button type="button" className="board-btn primary" onClick={() => void askCopilot()}>
                  Ask Copilot
                </button>
                {copilotA ? <div className="board-commentary">{copilotA}</div> : null}
              </div>
            )}

            {tab !== "copilot" && (
              <div className="board-commentary">
                <div className="board-commentary-lbl">Commentary · Claude</div>
                <p>{commentary?.what_happened || "Regenerate to pull live narrative from warehouse metrics."}</p>
                {commentary?.why_it_happened ? <p>{commentary.why_it_happened}</p> : null}
                {canAi ? (
                  <button
                    type="button"
                    className="board-btn"
                    disabled={regenerating}
                    onClick={() => void regenerateCommentary()}
                  >
                    {regenerating ? "Regenerating…" : "✦ Regenerate commentary"}
                  </button>
                ) : null}
              </div>
            )}
          </section>

          <footer className="board-footer">
            SMPL · Board Intelligence · Validation {payload.validation.status} · Confidential
          </footer>
        </>
      )}

      <style jsx global>{`
        .board-shell {
          min-height: 100vh;
          background: #18241b;
          color: #dde8d6;
          font-family: Inter, system-ui, sans-serif;
        }
        .board-topbar {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          padding: 16px 24px;
          border-bottom: 1px solid #2e3f31;
        }
        .board-logo {
          font-size: 18px;
          font-weight: 600;
        }
        .board-logo span {
          font-weight: 300;
          color: #72826a;
        }
        .board-sub {
          font-size: 12px;
          color: #aab8a2;
          margin-top: 4px;
        }
        .board-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
        }
        .board-btn {
          font-size: 12px;
          padding: 6px 12px;
          border-radius: 20px;
          border: 1px solid #2e3f31;
          background: #233326;
          color: #dde8d6;
          cursor: pointer;
          text-decoration: none;
        }
        .board-btn.primary {
          background: #c4855a;
          color: #18241b;
          border-color: #c4855a;
        }
        .board-nav {
          display: flex;
          gap: 0;
          overflow-x: auto;
          border-bottom: 1px solid #2e3f31;
          padding: 0 16px;
        }
        .board-nav-btn {
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          color: #72826a;
          padding: 10px 14px;
          cursor: pointer;
          font-size: 12px;
        }
        .board-nav-btn.active {
          color: #dde8d6;
          border-bottom-color: #c4855a;
          font-weight: 600;
        }
        .board-panel {
          padding: 20px 24px;
        }
        .board-error {
          background: rgba(184, 112, 95, 0.12);
          border-left: 3px solid #b8705f;
          margin: 16px 24px;
          border-radius: 8px;
        }
        .board-kpi-strip {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 10px;
          margin-top: 16px;
        }
        .board-kpi {
          background: #233326;
          border: 1px solid #2e3f31;
          border-radius: 12px;
          padding: 12px;
        }
        .board-kpi-lbl {
          font-size: 10px;
          text-transform: uppercase;
          color: #72826a;
        }
        .board-kpi-val {
          font-size: 20px;
          font-weight: 600;
          margin-top: 4px;
        }
        .board-kpi-delta {
          font-size: 11px;
          color: #5fa878;
          margin-top: 4px;
        }
        .board-ts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
          gap: 10px;
          margin: 16px 0;
        }
        .board-ts-card {
          background: #233326;
          border: 1px solid #2e3f31;
          border-radius: 10px;
          padding: 10px;
          font-size: 12px;
        }
        .board-ts-period {
          font-weight: 600;
          margin-bottom: 6px;
        }
        .board-commentary {
          margin-top: 16px;
          padding: 14px;
          border-left: 3px solid #c4855a;
          background: #233326;
          border-radius: 8px;
          line-height: 1.6;
          font-size: 13px;
          color: #aab8a2;
        }
        .board-commentary-lbl {
          font-size: 10px;
          text-transform: uppercase;
          color: #72826a;
          margin-bottom: 8px;
        }
        .board-copilot textarea {
          width: 100%;
          margin: 12px 0;
          background: #233326;
          border: 1px solid #2e3f31;
          color: #dde8d6;
          border-radius: 8px;
          padding: 10px;
        }
        .board-footer {
          padding: 12px 24px;
          border-top: 1px solid #2e3f31;
          font-size: 11px;
          color: #72826a;
        }
      `}</style>
    </div>
  );
}
