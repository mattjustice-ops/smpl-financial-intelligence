"use client";

import { useEffect, useState } from "react";

import { formatFetchError, getApiBase } from "../lib/apiBase";

type ValidationSummary = {
  status: "pass" | "warning" | "fail";
  failed_count: number;
  warning_count: number;
  passed_count: number;
};

type Props = {
  organizationId: string;
  scenario: string;
  startPeriod: string;
  endPeriod: string;
  /** Close month for MD&A (defaults to end period). Use posted close month, e.g. 2026-05 not 2026-12. */
  asOfPeriod?: string;
  marketingChannel?: string;
  disabled?: boolean;
  /** default | footer (collapsed) | featured (executive summary board/MD&A section) */
  variant?: "default" | "footer" | "featured";
};

function buildQuery(params: Record<string, string | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) q.set(key, value);
  });
  return q.toString();
}

async function fetchWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 120000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
        ...(init.headers ?? {}),
      },
    });
  } finally {
    window.clearTimeout(timeout);
  }
}

export function ReportingExportToolbar({
  organizationId,
  scenario,
  startPeriod,
  endPeriod,
  asOfPeriod: asOfPeriodProp,
  marketingChannel,
  disabled,
  variant = "default",
}: Props) {
  const apiBase = getApiBase();
  const [closeMonth, setCloseMonth] = useState(asOfPeriodProp ?? endPeriod);
  const [busy, setBusy] = useState<string | null>(null);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(false);
  const [includeAppendix, setIncludeAppendix] = useState(true);
  const [boardEngine, setBoardEngine] = useState<string | null>(null);
  const [lastExportEngine, setLastExportEngine] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [openaiModel, setOpenaiModel] = useState<string | null>(null);

  useEffect(() => {
    setCloseMonth(asOfPeriodProp ?? endPeriod);
  }, [asOfPeriodProp, endPeriod]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchWithTimeout(
          `${apiBase}/api/v1/export/ping?_=${Date.now()}`,
          { cache: "no-store" },
          8000,
        );
        if (!res.ok) return;
        const data = (await res.json()) as {
          board_engine?: string;
          openai_configured?: boolean;
          openai_model?: string;
        };
        if (!cancelled) {
          if (data.board_engine) setBoardEngine(data.board_engine);
          setAiConfigured(!!data.openai_configured);
          setOpenaiModel(data.openai_model ?? null);
        }
      } catch {
        if (!cancelled) setAiConfigured(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const asOf = closeMonth.trim() || endPeriod;

  const baseParams: Record<string, string | undefined> = {
    organization_id: organizationId,
    scenario,
    start_period: startPeriod,
    end_period: endPeriod,
    as_of_period: asOf,
    marketing_channel: marketingChannel || undefined,
    include_ai_commentary: includeAi ? "true" : "false",
    include_commentary: "true",
    include_appendix: includeAppendix ? "true" : "false",
    include_validation: "true",
  };

  const pingApi = async () => {
    const url = `${apiBase}/health`;
    try {
      const res = await fetchWithTimeout(url, {}, 8000);
      if (!res.ok) {
        throw new Error(`${url} returned HTTP ${res.status}`);
      }
    } catch (e) {
      throw new Error(formatFetchError(e, url));
    }
  };

  const runValidation = async () => {
    const url = `${apiBase}/api/v1/export/validation?${buildQuery(baseParams)}`;
    setBusy("validation");
    setError(null);
    setStatusLine("Running validation (may take 30–60s)…");
    try {
      await pingApi();
      const res = await fetchWithTimeout(url, {}, 120000);
      if (!res.ok) {
        throw new Error((await res.text()) || `Validation failed (${res.status})`);
      }
      setValidation((await res.json()) as ValidationSummary);
      setStatusLine(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatusLine(null);
    } finally {
      setBusy(null);
    }
  };

  const runExport = async (
    endpoint: string,
    filename: string,
    extraParams?: Record<string, string | undefined>
  ) => {
    const url = `${apiBase}/api/v1/export/${endpoint}?${buildQuery({ ...baseParams, ...extraParams })}`;
    setBusy(endpoint);
    setError(null);
    setStatusLine(
      "Building export on the server (1–3 min for full-year ranges). Keep the backend terminal open…"
    );
    try {
      await pingApi();
      const res = await fetchWithTimeout(url, {}, 300000);
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Export failed (HTTP ${res.status})`);
      }
      const engineHdr = res.headers.get("X-Board-Package-Engine");
      if (endpoint.includes("board")) {
        const resolved = engineHdr ?? boardEngine;
        setLastExportEngine(resolved);
        if (resolved && resolved !== "smpl-board-v2") {
          throw new Error(
            `Board export is from an old API build (engine=${resolved}). ` +
              `Restart backend: cd backend then .\\start-api.ps1`
          );
        }
        if (!resolved) {
          setStatusLine(
            "Download started (engine header not visible — confirm /export/ping shows smpl-board-v2)."
          );
        }
      }
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(objectUrl);
      setStatusLine("Download started.");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatusLine(null);
    } finally {
      setBusy(null);
    }
  };

  const isFooter = variant === "footer";
  const isFeatured = variant === "featured";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: isFooter ? 8 : 10,
        padding: isFooter ? 0 : isFeatured ? 0 : "12px 14px",
        border: isFooter || isFeatured ? "none" : "1px solid var(--border)",
        borderRadius: isFooter || isFeatured ? 0 : 8,
        background: isFooter || isFeatured ? "transparent" : "var(--panel)",
        flex: isFooter ? 1 : undefined,
        minWidth: isFooter ? 280 : undefined,
      }}
    >
      {isFeatured && featuredBody()}
      {isFooter && (
        <details>
          <summary style={{ fontSize: 11, color: "var(--muted)", cursor: "pointer", listStyle: "none" }}>
            Close exports ▾
          </summary>
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
            {exportBody(true)}
          </div>
        </details>
      )}
      {!isFooter && !isFeatured && (
        <>
          <strong style={{ fontSize: 13 }}>Close package exports (secondary)</strong>
          {exportBody(false)}
        </>
      )}
    </div>
  );

  function featuredBody() {
    type Artifact = {
      title: string;
      desc: string;
      endpoint: string;
      filename: string;
      extra?: Record<string, string>;
      primary?: boolean;
    };
    const artifacts: Artifact[] = [
      {
        title: "Board presentation",
        desc: "Full narrative PPTX — executive scorecard, GTM, ARR, cash, risks",
        endpoint: "board-package",
        filename: `board_package_${asOf}.pptx`,
        extra: { package_mode: "full_board" },
        primary: true,
      },
      {
        title: "MD&A workbook",
        desc: "Excel close package — variance tables, bridges, commentary tabs",
        endpoint: "month-end-close.xlsx",
        filename: `month_end_close_${asOf}.xlsx`,
      },
      {
        title: "Management review",
        desc: "Condensed leadership workbook for operating review",
        endpoint: "management-review.xlsx",
        filename: `management_review_${asOf}.xlsx`,
      },
      {
        title: "Variance commentary",
        desc: "Budget vs actual narrative lines by department and metric",
        endpoint: "variance-commentary.xlsx",
        filename: `variance_commentary_${asOf}.xlsx`,
      },
    ];

    return (
      <div className="os-close-package">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
          <div>
            <div className="os-section-label" style={{ paddingTop: 0 }}>
              Board &amp; MD&A close artifacts
            </div>
            <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
              Download board presentation, MD&amp;A workbook, and month-end close packages for the selected filters.
              {aiConfigured === false && " Add OPENAI_API_KEY to backend/secrets.env to include AI commentary in exports."}
            </p>
          </div>
          <button type="button" className="os-btn-ghost" disabled={disabled || !!busy || !organizationId} onClick={runValidation}>
            {busy === "validation" ? "Validating…" : "Run validation pre-check"}
          </button>
        </div>

        <div className="os-artifact-grid">
          {artifacts.map((a) => (
            <div key={a.endpoint} className={`os-artifact-card${a.primary ? " primary" : ""}`}>
              <div className="os-artifact-title">{a.title}</div>
              <div className="os-artifact-desc">{a.desc}</div>
              <button
                type="button"
                className={a.primary ? "os-btn-primary" : "os-btn-ghost"}
                style={{ marginTop: 10 }}
                disabled={disabled || !!busy || !organizationId}
                onClick={() => runExport(a.endpoint, a.filename, a.extra)}
              >
                {busy === a.endpoint ? "Building…" : "Download"}
              </button>
            </div>
          ))}
        </div>

        <div className="os-export-options">
          <label>
            Close month (as-of)
            <input
              type="text"
              value={closeMonth}
              onChange={(e) => setCloseMonth(e.target.value)}
              placeholder="YYYY-MM"
              disabled={!!busy}
            />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, flexDirection: "row", paddingTop: 18 }}>
            <input
              type="checkbox"
              checked={includeAi}
              onChange={(e) => setIncludeAi(e.target.checked)}
              disabled={!!busy}
            />
            Include ChatGPT commentary in exports
          </label>
          {includeAi && aiConfigured === false && (
            <span style={{ fontSize: 11, color: "var(--watch)", alignSelf: "center", maxWidth: 420, lineHeight: 1.4 }}>
              No API key on server. Add OPENAI_API_KEY to backend/secrets.env (see backend/scripts/import-openai-key.ps1), then restart
              .\start-api.ps1
            </span>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: 6, flexDirection: "row", paddingTop: 18 }}>
            <input
              type="checkbox"
              checked={includeAppendix}
              onChange={(e) => setIncludeAppendix(e.target.checked)}
              disabled={!!busy}
            />
            Validation appendix in board deck
          </label>
        </div>

        {boardEngine && (
          <p style={{ margin: "8px 0 0", fontSize: 11, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
            Board engine: {boardEngine}
            {lastExportEngine ? ` · last export: ${lastExportEngine}` : ""}
          </p>
        )}
        {statusLine && <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--muted)" }}>{statusLine}</p>}
        {validation && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: validation.status === "fail" ? "var(--negative)" : "var(--muted)" }}>
            Validation: {validation.status} — {validation.passed_count} passed, {validation.warning_count} warnings,{" "}
            {validation.failed_count} failed.
          </p>
        )}
        {error && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--negative)", whiteSpace: "pre-wrap" }}>{error}</p>
        )}
      </div>
    );
  }

  function exportBody(compact: boolean) {
    return (
      <>
      {!compact && (
      <p style={{ margin: 0, fontSize: 11, color: "var(--muted)", fontFamily: "ui-monospace, monospace" }}>
        API: {apiBase}
        {boardEngine ? ` · board engine: ${boardEngine}` : " · board engine: (start API to detect)"}
      </p>
      )}
      {lastExportEngine && !compact && (
        <p style={{ margin: 0, fontSize: 11, color: "#15803d" }}>
          Last board export engine: {lastExportEngine}
        </p>
      )}
      <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
        <span style={{ color: "var(--muted)" }}>
          Close month (as-of) — use last posted actual month (e.g. 2026-05), not always End period
        </span>
        <input
          type="text"
          value={closeMonth}
          onChange={(e) => setCloseMonth(e.target.value)}
          placeholder="YYYY-MM"
          disabled={!!busy}
          style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", maxWidth: 120 }}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--muted)" }}>
        <input type="checkbox" checked={includeAi} onChange={(e) => setIncludeAi(e.target.checked)} disabled={!!busy} />
        Include AI draft commentary (requires OPENAI_API_KEY on backend)
      </label>
      {includeAi && aiConfigured === false && (
        <p style={{ margin: 0, fontSize: 11, color: "var(--watch)" }}>
          OPENAI_API_KEY not detected on server — exports will use rules-based commentary.
        </p>
      )}
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--muted)" }}>
        <input
          type="checkbox"
          checked={includeAppendix}
          onChange={(e) => setIncludeAppendix(e.target.checked)}
          disabled={!!busy}
        />
        Include validation appendix in board deck
      </label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: compact ? 6 : 8 }}>
        <button
          type="button"
          className={compact ? "os-btn-ghost" : undefined}
          disabled={disabled || !!busy || !organizationId}
          onClick={runValidation}
        >
          {busy === "validation" ? "Checking…" : compact ? "Validate" : "Run validation pre-check"}
        </button>
        <button
          type="button"
          className={compact ? "os-btn-ghost" : undefined}
          disabled={disabled || !!busy || !organizationId}
          onClick={() => runExport("month-end-close.xlsx", `month_end_close_${asOf}.xlsx`)}
        >
          {compact ? "MD&A Excel" : "Export Excel close package (MD&A)"}
        </button>
        <button
          type="button"
          className={compact ? "os-btn-ghost" : undefined}
          disabled={disabled || !!busy || !organizationId}
          onClick={() => runExport("management-review.xlsx", `management_review_${asOf}.xlsx`)}
        >
          {compact ? "Mgmt review" : "Export management review"}
        </button>
        <button
          type="button"
          className={compact ? "os-btn-ghost" : undefined}
          disabled={disabled || !!busy || !organizationId}
          onClick={() => runExport("variance-commentary.xlsx", `variance_commentary_${asOf}.xlsx`)}
        >
          {compact ? "Variance" : "Export variance commentary"}
        </button>
        <button
          type="button"
          className={compact ? "os-btn-ghost" : undefined}
          disabled={disabled || !!busy || !organizationId}
          onClick={() =>
            runExport("board-package", `board_package_${asOf}.pptx`, { package_mode: "full_board" })
          }
        >
          {compact ? "Board PPTX" : "Export Board Package"}
        </button>
      </div>
      {statusLine && (
        <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>{statusLine}</p>
      )}
      {validation && (
        <p style={{ margin: 0, fontSize: 12, color: validation.status === "fail" ? "#b42318" : "var(--muted)" }}>
          Validation: {validation.status} — {validation.passed_count} passed, {validation.warning_count} warnings,{" "}
          {validation.failed_count} failed.
        </p>
      )}
      {error && (
        <p style={{ margin: 0, fontSize: 12, color: "#b42318", lineHeight: 1.45, whiteSpace: "pre-wrap" }}>
          {error}
        </p>
      )}
      </>
    );
  }
}
