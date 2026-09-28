"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";

type Question = {
  id: string;
  section: string;
  prompt: string;
  choices: string[];
  effect?: string;
  consequence?: string;
  customer_action?: string;
};

type ModuleObject = {
  id: string;
  name: string;
  connector: string;
  present: boolean;
  confidence: number;
  sources: string[];
  missing_periods: string[];
};

type ModuleRow = {
  id: string;
  name: string;
  status: "READY" | "PARTIAL" | "UNAVAILABLE";
  reasons: string[];
  confidence: number;
  weight: number;
  ready_threshold: number;
  required_objects: ModuleObject[];
  improvement_paths: Array<{ kind: string; text: string }>;
};

type ReadinessPayload = {
  readiness_score: number | null;
  score_state: "final" | "provisional" | "not_scored";
  reporting_window: { as_of: string; start: string; end: string };
  answers: Record<string, string>;
  answers_updated_at: string | null;
  gates: { status: string; failed: string[]; pending: string[] };
  normalization_gates: Array<{ id: string; name: string; resolved: boolean; unresolved_questions: string[] }>;
  summary: { ready: number; partial: number; unavailable: number; modules: number };
  modules: ModuleRow[];
  recommended_next: Array<{
    kind: string;
    ref: string;
    label: string;
    expected_delta: number;
    expected_score: number;
    modules_to_ready: string[];
  }>;
  method: Record<string, string>;
  questions: {
    readiness_gates: Question[];
    normalization_gates: Array<{ id: string; name: string; questions: Question[] }>;
    score_inputs: Question[];
  };
};

const STATUS_CLASS: Record<string, string> = {
  READY: "border-teal-500/40 bg-teal-500/10 text-teal-200",
  PARTIAL: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  UNAVAILABLE: "border-rose-500/40 bg-rose-500/10 text-rose-200",
};

const REASON_LABEL: Record<string, string> = {
  CONFIDENCE_BELOW_READY_THRESHOLD: "Confidence below ready threshold",
  MISSING_REQUIRED_OBJECTS: "Missing required data",
  STRUCTURAL_CEILING: "Connector limitation",
  INSUFFICIENT_CONFIDENCE: "Insufficient confidence",
  GATE_UNRESOLVED: "Normalization gate unresolved",
  POLICY_GAP: "Accounting policy gap",
};

const KIND_LABEL: Record<string, string> = {
  connector: "SMPL connector",
  customer_action: "Customer action",
  questionnaire: "Questionnaire",
  structural: "Limitation",
};

function choiceLabel(c: string): string {
  return c.replace(/_/g, " ");
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function ReadinessPanel({ organizationId }: { organizationId: string }) {
  const [data, setData] = useState<ReadinessPayload | null>(null);
  const [draft, setDraft] = useState<Record<string, string | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openModule, setOpenModule] = useState<string | null>(null);

  const url = useCallback(
    (path = "") => `/api/v1/readiness${path}?organization_id=${encodeURIComponent(organizationId)}`,
    [organizationId],
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(url(), { cache: "no-store" });
      if (!res.ok) throw new Error(`Readiness API returned ${res.status}`);
      setData((await res.json()) as ReadinessPayload);
      setDraft({});
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [url]);

  useEffect(() => {
    void load();
  }, [load]);

  const answerFor = (id: string): string => {
    if (id in draft) return draft[id] ?? "";
    return data?.answers[id] ?? "";
  };

  const dirty = Object.keys(draft).length > 0;

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(url("/answers"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: draft }),
        cache: "no-store",
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errs = body?.detail?.errors;
        throw new Error(Array.isArray(errs) ? errs.join("; ") : `Save failed (${res.status})`);
      }
      setData(body as ReadinessPayload);
      setDraft({});
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const stateText = useMemo(() => {
    if (!data) return "";
    if (data.score_state === "not_scored")
      return `Not scored — readiness gate ${data.gates.failed.join(", ")} failed. Onboarding pauses until the customer resolves it.`;
    if (data.score_state === "provisional")
      return `Provisional — readiness gates ${data.gates.pending.join(", ")} not yet answered.`;
    return "Final — all readiness gates pass.";
  }, [data]);

  if (!data && !error) {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4 text-sm text-slate-400">
        Loading readiness…
      </div>
    );
  }

  const questionRow = (q: Question) => (
    <li key={q.id} className="flex flex-wrap items-start justify-between gap-3 py-2">
      <div className="min-w-0 flex-1">
        <p className="text-sm text-slate-200">
          <span className="mr-2 font-mono text-xs text-slate-500">{q.id}</span>
          {q.prompt}
        </p>
        {q.consequence ? (
          <p className="mt-0.5 text-xs text-slate-500">
            If no: {q.consequence}. <span className="text-slate-400">{q.customer_action}.</span>
          </p>
        ) : null}
      </div>
      <select
        value={answerFor(q.id)}
        onChange={(e) => setDraft((d) => ({ ...d, [q.id]: e.target.value || null }))}
        className="rounded-md border border-white/15 bg-slate-950 px-2 py-1 text-xs text-slate-200"
      >
        <option value="">Not answered</option>
        {q.choices.map((c) => (
          <option key={c} value={c}>
            {choiceLabel(c)}
          </option>
        ))}
      </select>
    </li>
  );

  return (
    <section className="space-y-5">
      <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Onboarding Readiness Score</h2>
            <p className="mt-1 max-w-2xl text-xs text-slate-400">
              What SMPL can report from the data as loaded, module by module. The customer owns the
              data and the process that creates it — every gap below is closed by a customer action,
              a connector, or a questionnaire decision, never by SMPL adjusting the data.
            </p>
            {data ? (
              <p className="mt-2 text-xs text-slate-500">
                Reporting window {data.reporting_window.start} – {data.reporting_window.end} · close{" "}
                {data.reporting_window.as_of}
              </p>
            ) : null}
          </div>
          <div className="text-right">
            <div className="font-mono text-3xl text-teal-300">
              {data?.readiness_score == null ? "—" : `${data.readiness_score.toFixed(1)}%`}
            </div>
            <div className="text-xs text-slate-400">
              {data?.summary.ready ?? 0} ready · {data?.summary.partial ?? 0} partial ·{" "}
              {data?.summary.unavailable ?? 0} unavailable
            </div>
          </div>
        </div>
        {data ? (
          <p
            className={`mt-3 rounded-md border px-3 py-2 text-xs ${
              data.score_state === "not_scored"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-100"
                : data.score_state === "provisional"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
                  : "border-teal-500/30 bg-teal-500/10 text-teal-100"
            }`}
          >
            {stateText}
          </p>
        ) : null}
        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      </div>

      {data && data.recommended_next.length ? (
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Biggest next improvements
          </h3>
          <ul className="mt-2 divide-y divide-white/5">
            {data.recommended_next.slice(0, 6).map((r) => (
              <li key={`${r.kind}-${r.ref}`} className="flex flex-wrap items-baseline gap-x-3 py-2 text-sm">
                <span className="font-mono text-teal-300">+{r.expected_delta.toFixed(1)}</span>
                <span className="text-slate-200">{r.label}</span>
                <span className="text-xs uppercase tracking-wide text-slate-600">{KIND_LABEL[r.kind] ?? r.kind}</span>
                {r.modules_to_ready.length ? (
                  <span className="text-xs text-slate-500">→ READY: {r.modules_to_ready.join(", ")}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {data ? (
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Modules</h3>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="text-xs text-slate-500">
              <tr>
                <th className="py-1 font-normal">Module</th>
                <th className="py-1 font-normal">Status</th>
                <th className="py-1 text-right font-normal">Confidence</th>
                <th className="py-1 text-right font-normal">Ready at</th>
                <th className="py-1 text-right font-normal">Weight</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.modules.map((m) => (
                <Fragment key={m.id}>
                  <tr
                    className="cursor-pointer hover:bg-white/5"
                    onClick={() => setOpenModule(openModule === m.id ? null : m.id)}
                  >
                    <td className="py-1.5 text-slate-200">
                      <span className="mr-1 text-slate-600">{openModule === m.id ? "▾" : "▸"}</span>
                      {m.name}
                      {m.reasons.length ? (
                        <span className="ml-2 text-xs text-slate-500">
                          {m.reasons.map((r) => REASON_LABEL[r] ?? r).join(" · ")}
                        </span>
                      ) : null}
                    </td>
                    <td className="py-1.5">
                      <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${STATUS_CLASS[m.status]}`}>
                        {m.status}
                      </span>
                    </td>
                    <td className="py-1.5 text-right font-mono text-xs text-slate-300">{pct(m.confidence)}</td>
                    <td className="py-1.5 text-right font-mono text-xs text-slate-500">{pct(m.ready_threshold)}</td>
                    <td className="py-1.5 text-right font-mono text-xs text-slate-500">{m.weight}</td>
                  </tr>
                  {openModule === m.id ? (
                    <tr>
                      <td colSpan={5} className="bg-slate-950/40 px-3 py-2">
                        <ul className="grid gap-1 text-xs text-slate-400 sm:grid-cols-2">
                          {m.required_objects.map((o) => (
                            <li key={o.id}>
                              <span className={o.present ? "text-teal-300" : "text-rose-300"}>{o.present ? "✓" : "✗"}</span>{" "}
                              <span className="text-slate-300">{o.name}</span>{" "}
                              <span className="text-slate-600">
                                {o.present ? `${pct(o.confidence)} · ${o.sources.join(", ")}` : `needs ${o.connector}`}
                              </span>
                            </li>
                          ))}
                        </ul>
                        {m.improvement_paths.length ? (
                          <ul className="mt-2 space-y-0.5 text-xs text-amber-100/80">
                            {m.improvement_paths.map((p, i) => (
                              <li key={i}>→ {p.text}</li>
                            ))}
                          </ul>
                        ) : null}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {data ? (
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Discovery questionnaire inputs
            </h3>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy || !dirty}
                onClick={() => void save()}
                className="rounded-md border border-teal-500/40 bg-teal-500/10 px-3 py-1.5 text-xs text-teal-200 hover:bg-teal-500/20 disabled:opacity-40"
              >
                {busy ? "Saving…" : "Save answers & rescore"}
              </button>
              <button
                type="button"
                disabled={busy || !dirty}
                onClick={() => setDraft({})}
                className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-slate-400 disabled:opacity-40"
              >
                Discard
              </button>
            </div>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Section numbers match the Customer Onboarding Discovery Call Sheet.
            {data.answers_updated_at ? ` Last saved ${new Date(data.answers_updated_at).toLocaleString()}.` : ""}
          </p>

          <h4 className="mt-4 text-xs font-medium text-slate-300">0 · Readiness gates — any “no” stops scoring</h4>
          <ul className="divide-y divide-white/5">{data.questions.readiness_gates.map(questionRow)}</ul>

          {data.questions.normalization_gates.map((g) => {
            const st = data.normalization_gates.find((x) => x.id === g.id);
            return (
              <div key={g.id}>
                <h4 className="mt-4 text-xs font-medium text-slate-300">
                  {g.name}{" "}
                  <span className={st?.resolved ? "text-teal-300" : "text-amber-300"}>
                    {st?.resolved ? "· resolved" : "· unresolved"}
                  </span>
                </h4>
                <ul className="divide-y divide-white/5">{g.questions.map(questionRow)}</ul>
              </div>
            );
          })}

          <h4 className="mt-4 text-xs font-medium text-slate-300">7.7–7.13 · Accounting policy &amp; close practice</h4>
          <ul className="divide-y divide-white/5">{data.questions.score_inputs.map(questionRow)}</ul>

          <details className="mt-4 text-xs text-slate-500">
            <summary className="cursor-pointer">How the score is calculated</summary>
            <ul className="mt-1 space-y-0.5">
              {Object.entries(data.method).map(([k, v]) => (
                <li key={k}>{v}</li>
              ))}
            </ul>
          </details>
        </div>
      ) : null}
    </section>
  );
}
