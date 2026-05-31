"use client";

import { useCallback, useEffect, useState } from "react";

import { formatFetchError, getApiBase } from "../../lib/apiBase";
import { CommentaryPanel } from "./CommentaryPanel";

type CommentaryBlock = {
  what_happened: string;
  why_it_happened: string;
  impact: string;
  favorable: string;
  unfavorable: string;
  recommended_actions: string;
  leadership_watch: string;
};

type CommentaryResponse = {
  as_of_period: string;
  ai_configured: boolean;
  used_ai: boolean;
  openai_model: string;
  narrative: string;
  mda_narrative: string;
  executive_summary: CommentaryBlock;
};

type Props = {
  organizationId: string;
  scenario: string;
  startPeriod: string;
  endPeriod: string;
  asOfPeriod: string;
  marketingChannel?: string;
  disabled?: boolean;
};

function buildQuery(params: Record<string, string | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) q.set(key, value);
  });
  return q.toString();
}

export function ExecutiveAiCommentary({
  organizationId,
  scenario,
  startPeriod,
  endPeriod,
  asOfPeriod,
  marketingChannel,
  disabled,
}: Props) {
  const apiBase = getApiBase();
  const [useAi, setUseAi] = useState(false);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [openaiModel, setOpenaiModel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CommentaryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/api/v1/export/ping?_=${Date.now()}`, {
          cache: "no-store",
        });
        if (!res.ok) return;
        const ping = (await res.json()) as { openai_configured?: boolean; openai_model?: string };
        if (!cancelled) {
          setAiConfigured(!!ping.openai_configured);
          setOpenaiModel(ping.openai_model ?? null);
        }
      } catch {
        if (!cancelled) setAiConfigured(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const load = useCallback(async () => {
    if (!organizationId || disabled) return;
    const url = `${apiBase}/api/v1/export/executive-commentary?${buildQuery({
      organization_id: organizationId,
      scenario,
      start_period: startPeriod,
      end_period: endPeriod,
      as_of_period: asOfPeriod,
      marketing_channel: marketingChannel || undefined,
      use_ai: useAi ? "true" : "false",
    })}`;
    setBusy(true);
    setError(null);
    try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 120000);
      const res = await fetch(url, { cache: "no-store", signal: controller.signal });
      window.clearTimeout(timeout);
      if (!res.ok) {
        throw new Error((await res.text()) || `Commentary failed (${res.status})`);
      }
      setData((await res.json()) as CommentaryResponse);
    } catch (e) {
      setError(formatFetchError(e, url));
      setData(null);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    organizationId,
    scenario,
    startPeriod,
    endPeriod,
    asOfPeriod,
    marketingChannel,
    useAi,
    disabled,
  ]);

  const narrative = data?.narrative?.trim() ?? "";
  const usedAi = data?.used_ai;

  return (
    <div className="os-panel" style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div className="os-section-label" style={{ paddingTop: 0 }}>
            AI executive commentary
          </div>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
            {aiConfigured === false && (
              <>
                Set <code>OPENAI_API_KEY</code> in <code>backend/secrets.env</code> (or run{" "}
                <code>backend/scripts/import-openai-key.ps1</code> with your Notepad file path), then restart the API.
              </>
            )}
            {aiConfigured === true && (
              <>
                Connected via API · {openaiModel ?? "OpenAI"} · same engine as board deck &amp; MD&A exports
              </>
            )}
            {aiConfigured === null && "Checking OpenAI configuration…"}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--muted)" }}>
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
              disabled={busy}
            />
            Use ChatGPT
          </label>
          <button type="button" className="os-btn-ghost" onClick={load} disabled={busy || disabled || !organizationId}>
            {busy ? "Generating…" : "Regenerate"}
          </button>
        </div>
      </div>

      {busy && !narrative && (
        <p style={{ margin: "12px 0 0", fontSize: 12, color: "var(--muted)" }}>
          Drafting commentary from warehouse metrics…
        </p>
      )}

      {narrative ? (
        <CommentaryPanel
          label={usedAi ? "Executive takeaway (AI)" : "Executive takeaway (rules-based)"}
          text={narrative}
          variant={data?.executive_summary?.unfavorable ? "risk" : "default"}
        />
      ) : (
        !busy &&
        !error && (
          <p style={{ margin: "12px 0 0", fontSize: 12, color: "var(--muted)" }}>
            Click Regenerate to draft executive commentary from current filters. Optionally enable Use ChatGPT before
            regenerating.
          </p>
        )
      )}

      {error && (
        <p style={{ margin: "10px 0 0", fontSize: 12, color: "var(--negative)", whiteSpace: "pre-wrap" }}>{error}</p>
      )}
    </div>
  );
}
