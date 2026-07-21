"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  looksLikeQuestion,
  normalizeUtterance,
} from "@/lib/sales-talk/retrieve";
import type {
  SalesAudience,
  SalesTalkAnswerResponse,
} from "@/lib/sales-talk/types";

type ListeningState = "idle" | "listening" | "paused" | "unsupported";

type AnswerCard = SalesTalkAnswerResponse & {
  id: string;
  at: number;
};

type SpeechRecognitionAlternativeLike = { transcript: string };
type SpeechRecognitionResultLike = {
  isFinal: boolean;
  0: SpeechRecognitionAlternativeLike;
};
type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike> & { length: number };
};
type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

const AUDIENCE_OPTIONS: Array<{ id: SalesAudience; label: string }> = [
  { id: "general", label: "General" },
  { id: "cfo", label: "CFO" },
  { id: "fpa", label: "FP&A" },
  { id: "ceo", label: "CEO" },
  { id: "it", label: "IT" },
  { id: "engineer", label: "Engineer" },
  { id: "investor", label: "Investor" },
];

const DEBOUNCE_MS = 20_000;
const DEFAULT_DEFLECT =
  "Good question — I want to give you an exact figure rather than guess, so let me follow up right after this.";

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function confidenceBadge(confidence: SalesTalkAnswerResponse["confidence"] | null) {
  if (confidence === "verified") {
    return {
      label: "Verified",
      className: "border-teal-400/40 bg-teal-400/15 text-teal-200",
    };
  }
  if (confidence === "directional") {
    return {
      label: "Directional",
      className: "border-amber-400/40 bg-amber-400/15 text-amber-200",
    };
  }
  if (confidence === "do-not-answer") {
    return {
      label: "Deflect",
      className: "border-rose-400/40 bg-rose-400/15 text-rose-200",
    };
  }
  return {
    label: "No answer",
    className: "border-rose-400/40 bg-rose-400/15 text-rose-200",
  };
}

export function SalesTalkTrack() {
  const [listeningState, setListeningState] = useState<ListeningState>("idle");
  const [audience, setAudience] = useState<SalesAudience>("general");
  const [includeInternalDeep, setIncludeInternalDeep] = useState(false);
  const [rephrase, setRephrase] = useState(true);
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [cards, setCards] = useState<AnswerCard[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualQuestion, setManualQuestion] = useState("");
  const [speechSupported, setSpeechSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const wantListenRef = useRef(false);
  const lastAskedRef = useRef<{ norm: string; at: number } | null>(null);
  const audienceRef = useRef(audience);
  const includeInternalRef = useRef(includeInternalDeep);
  const rephraseRef = useRef(rephrase);
  const askingRef = useRef(false);

  useEffect(() => {
    audienceRef.current = audience;
  }, [audience]);
  useEffect(() => {
    includeInternalRef.current = includeInternalDeep;
  }, [includeInternalDeep]);
  useEffect(() => {
    rephraseRef.current = rephrase;
  }, [rephrase]);

  const askQuestion = useCallback(async (question: string, source: "live" | "manual") => {
    const trimmed = question.trim();
    if (trimmed.length < 8) return;

    const norm = normalizeUtterance(trimmed);
    const now = Date.now();
    const last = lastAskedRef.current;
    if (last && last.norm === norm && now - last.at < DEBOUNCE_MS) {
      return;
    }
    if (askingRef.current) return;

    lastAskedRef.current = { norm, at: now };
    askingRef.current = true;
    setBusy(true);
    setError(null);

    try {
      const res = await fetch("/api/sales-talk/answer", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          audience: audienceRef.current,
          includeInternalDeep: includeInternalRef.current,
          rephrase: rephraseRef.current,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `Answer API returned ${res.status}`);
      }
      const data = (await res.json()) as SalesTalkAnswerResponse;
      setCards((prev) => [
        {
          ...data,
          id: `${now}-${source}-${Math.random().toString(36).slice(2, 8)}`,
          at: now,
        },
        ...prev,
      ].slice(0, 12));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      askingRef.current = false;
      setBusy(false);
    }
  }, []);

  const stopRecognition = useCallback(() => {
    wantListenRef.current = false;
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.onend = null;
        rec.stop();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    }
  }, []);

  const startRecognition = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setSpeechSupported(false);
      setListeningState("unsupported");
      setError(
        "Web Speech API is not available in this browser. Use Chrome on desktop for live listening.",
      );
      return;
    }

    stopRecognition();
    wantListenRef.current = true;

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let interim = "";
      const finals: string[] = [];
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result?.[0]?.transcript?.trim() ?? "";
        if (!text) continue;
        if (result.isFinal) {
          finals.push(text);
        } else {
          interim += (interim ? " " : "") + text;
        }
      }
      setInterimTranscript(interim);

      for (const finalText of finals) {
        setFinalTranscript((prev) => {
          const next = prev ? `${prev} ${finalText}` : finalText;
          return next.length > 4000 ? next.slice(-4000) : next;
        });
        if (looksLikeQuestion(finalText)) {
          void askQuestion(finalText, "live");
        }
      }
    };

    recognition.onerror = (event) => {
      const code = event.error ?? "unknown";
      if (code === "not-allowed" || code === "service-not-allowed") {
        setError("Microphone permission denied. Allow mic access for this site, then Start listening.");
        wantListenRef.current = false;
        setListeningState("idle");
        return;
      }
      if (code === "aborted" || code === "no-speech") {
        return;
      }
      setError(`Speech recognition error: ${code}`);
    };

    recognition.onend = () => {
      // Chrome often ends continuous sessions; restart while user wants listening.
      if (wantListenRef.current) {
        try {
          recognition.start();
          setListeningState("listening");
        } catch {
          setListeningState("paused");
          wantListenRef.current = false;
        }
      } else {
        setListeningState((prev) => (prev === "unsupported" ? prev : "paused"));
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListeningState("listening");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start microphone.");
      setListeningState("idle");
      wantListenRef.current = false;
    }
  }, [askQuestion, stopRecognition]);

  useEffect(() => {
    const supported = Boolean(getSpeechRecognitionCtor());
    setSpeechSupported(supported);
    if (!supported) setListeningState("unsupported");
    return () => {
      wantListenRef.current = false;
      stopRecognition();
    };
  }, [stopRecognition]);

  // Optional Space hotkey: hold to ensure listening (starts if idle)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat) return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (listeningState === "unsupported") return;
      e.preventDefault();
      if (listeningState !== "listening") startRecognition();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [listeningState, startRecognition]);

  const clearAll = () => {
    setFinalTranscript("");
    setInterimTranscript("");
    setCards([]);
    setManualQuestion("");
    setError(null);
    lastAskedRef.current = null;
  };

  const pauseListening = () => {
    wantListenRef.current = false;
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    setListeningState("paused");
    setInterimTranscript("");
  };

  const listening = listeningState === "listening";

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 md:py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-400">
            Internal · Sales Talk Track
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Live meeting aide
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-400">
            Mic listens → detects a prospect question → surfaces a vetted KB answer (or a deflect
            card). Never invents numbers. Not the in-product finance Copilot.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/app/ops"
            className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            Ops
          </Link>
          <Link
            href="/app"
            className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            App
          </Link>
        </div>
      </div>

      {/* Mic disclosure + controls */}
      <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex h-3 w-3 rounded-full ${
                listening ? "animate-pulse bg-teal-400 shadow-[0_0_12px_rgba(34,203,197,0.8)]" : "bg-slate-600"
              }`}
              aria-hidden
            />
            <div>
              <p className="text-sm font-medium text-white">
                {listening
                  ? "Microphone is on — listening"
                  : listeningState === "paused"
                    ? "Paused"
                    : listeningState === "unsupported"
                      ? "Speech recognition unavailable"
                      : "Microphone off"}
              </p>
              <p className="text-xs text-slate-500">
                Disclose to the room that an AI assistant is running for notes/reference.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => startRecognition()}
              disabled={!speechSupported || listening}
              className="rounded-lg border border-teal-400/40 bg-teal-400/15 px-3 py-2 text-sm font-medium text-teal-100 hover:bg-teal-400/25 disabled:opacity-40"
            >
              Start listening
            </button>
            <button
              type="button"
              onClick={pauseListening}
              disabled={!listening}
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-40"
            >
              Pause
            </button>
            <button
              type="button"
              onClick={clearAll}
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10"
            >
              Clear
            </button>
          </div>
        </div>

        {!speechSupported ? (
          <p className="mt-4 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
            This browser does not expose <code>SpeechRecognition</code>. Open Chrome on desktop for
            live mic capture. Electron / Whisper loopback is a follow-up if Web Speech proves
            insufficient.
          </p>
        ) : null}

        {error ? (
          <p className="mt-4 rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-100">
            {error}
          </p>
        ) : null}
      </section>

      {/* Audience + options */}
      <section className="mb-6 grid gap-4 md:grid-cols-[1fr_auto]">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Audience mode
          </p>
          <div className="flex flex-wrap gap-2">
            {AUDIENCE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setAudience(opt.id)}
                className={`rounded-lg border px-3 py-1.5 text-sm ${
                  audience === opt.id
                    ? "border-teal-400/50 bg-teal-400/15 text-teal-100"
                    : "border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/5"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col justify-end gap-2 text-sm text-slate-300">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeInternalDeep}
              onChange={(e) => setIncludeInternalDeep(e.target.checked)}
              className="rounded border-white/20 bg-slate-900"
            />
            Include internal deep
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={rephrase}
              onChange={(e) => setRephrase(e.target.checked)}
              className="rounded border-white/20 bg-slate-900"
            />
            Rephrase for audience (no new facts)
          </label>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Transcript */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Rolling transcript</h2>
            {busy ? <span className="text-xs text-teal-300">Retrieving…</span> : null}
          </div>
          <div className="min-h-[220px] max-h-[360px] overflow-y-auto rounded-xl bg-black/30 p-4 text-sm leading-relaxed text-slate-300">
            {finalTranscript || interimTranscript ? (
              <>
                <span>{finalTranscript}</span>
                {interimTranscript ? (
                  <span className="text-slate-500"> {interimTranscript}</span>
                ) : null}
              </>
            ) : (
              <span className="text-slate-600">
                Start listening. Final utterances that look like questions trigger retrieval
                automatically.
              </span>
            )}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Session-only — not written to disk. Optional: press Space to start listening if paused.
          </p>

          <div className="mt-4 border-t border-white/10 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
              Manual trigger (if detection misses)
            </p>
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void askQuestion(manualQuestion, "manual");
                setManualQuestion("");
              }}
            >
              <input
                value={manualQuestion}
                onChange={(e) => setManualQuestion(e.target.value)}
                placeholder="Type a heard question…"
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-slate-600"
              />
              <button
                type="submit"
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10"
              >
                Ask
              </button>
            </form>
          </div>
        </section>

        {/* Answer cards */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-white">Answer cards</h2>
          {cards.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-6 text-sm text-slate-500">
              Waiting for a question. When the KB has no coverage, you&apos;ll get a clear{" "}
              <span className="text-rose-300">No prepared answer</span> deflect card — never
              invented figures.
            </div>
          ) : null}
          {cards.map((card) => {
            const badge = confidenceBadge(
              card.status === "no_prepared_answer" ? null : card.confidence,
            );
            const isDeflect =
              card.status === "deflect" || card.status === "no_prepared_answer";
            return (
              <article
                key={card.id}
                className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-lg shadow-black/20"
              >
                <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                  <p className="max-w-[75%] text-xs text-slate-500">{card.question}</p>
                  <span
                    className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${badge.className}`}
                  >
                    {badge.label}
                  </span>
                </div>

                {isDeflect ? (
                  <>
                    <h3 className="text-lg font-semibold text-white">No prepared answer</h3>
                    <p className="mt-2 text-base leading-relaxed text-slate-100">
                      Safe deflection: &ldquo;{card.deflectScript || DEFAULT_DEFLECT}&rdquo;
                    </p>
                    {card.entryId ? (
                      <p className="mt-3 text-xs text-slate-500">
                        Topic flagged · {card.entryId}
                        {card.source ? ` · ${card.source}` : ""}
                      </p>
                    ) : (
                      <p className="mt-3 text-xs text-slate-500">
                        No KB match — do not invent numbers. Note for follow-up.
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-semibold text-white">
                      {card.title ?? "Answer"}
                    </h3>
                    <p className="mt-2 text-base leading-relaxed text-slate-100">
                      {card.answer}
                    </p>
                    <p className="mt-3 text-xs text-slate-500">
                      Source · {card.entryId}
                      {card.source ? ` · ${card.source}` : ""}
                      {card.rephrased ? " · rephrased" : " · raw KB"}
                      {card.score != null ? ` · score ${card.score.toFixed(1)}` : ""}
                    </p>
                  </>
                )}
              </article>
            );
          })}
        </section>
      </div>

      <footer className="mt-10 border-t border-white/10 pt-4 text-xs leading-relaxed text-slate-500">
        <p>
          Privacy: audio is not persisted to disk by this app. The rolling transcript stays in this
          browser session only. Browser Web Speech may send audio to the browser vendor&apos;s cloud
          STT (often Google in Chrome, Apple on Safari) — treat customer/investor calls accordingly.
        </p>
        <p className="mt-2">
          KB path:{" "}
          <code className="text-slate-400">frontend/content/sales-kb/knowledge_base.json</code>
          {" · "}
          Docs: <code className="text-slate-400">docs/SALES_TALK_TRACK.md</code>
        </p>
      </footer>
    </main>
  );
}
