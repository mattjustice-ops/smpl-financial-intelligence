import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { BOOK_DEMO_URL, HERO_COMMENTARY } from "../constants";
import { GlowOrb } from "../motion";

const KPIS = [
  { label: "ARR", value: "$83.4M", delta: "+$0.1M vs plan", accent: "#5eead4", spark: [72, 74, 76, 79, 83], color: "#2dd4bf" },
  { label: "Revenue", value: "$7.18M", delta: "+1.1% vs plan", accent: "#67e8f9", spark: [6.2, 6.5, 6.7, 6.9, 7.2], color: "#22d3ee" },
  { label: "Cash", value: "$66.0M", delta: "+$37.4M vs plan", accent: "#6ee7b7", spark: [48, 51, 58, 62, 66], color: "#34d399" },
  { label: "Rule of 40", value: "28%", delta: "Improving", accent: "#c4b5fd", spark: [22, 24, 25, 26, 28], color: "#a78bfa" },
  { label: "Pipeline Coverage", value: "2.4×", delta: "New logo risk", accent: "#fcd34d", spark: [3.1, 2.9, 2.7, 2.5, 2.4], color: "#fbbf24" },
  { label: "Headcount", value: "412", delta: "+2% vs plan", accent: "#7dd3fc", spark: [398, 402, 405, 408, 412], color: "#38bdf8" },
];

function sparklinePath(points: number[]) {
  const w = 64;
  const h = 28;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = w / (points.length - 1);

  return points
    .map((p, i) => {
      const x = i * step;
      const y = h - ((p - min) / range) * (h - 4) - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function HeroSection() {
  return (
    <section
      className="relative overflow-hidden bg-slate-950 px-6 pb-20 pt-16 md:pb-28 md:pt-24"
      style={{ color: "#fff" }}
    >
      <GlowOrb className="left-1/4 top-0 h-[420px] w-[420px] bg-teal-500/20" />
      <GlowOrb className="bottom-0 right-0 h-[360px] w-[360px] bg-violet-600/15" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(45,212,191,0.18),transparent)]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 lg:grid-cols-[1fr_1.05fr]">
        <div>
          <p className="mb-5 text-sm font-medium tracking-wide" style={{ color: "rgba(94, 234, 212, 0.9)" }}>
            Make every SaaS company operate like it has a world-class CFO team.
          </p>
          <h1
            className="max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl md:text-6xl lg:text-[3.35rem]"
            style={{ color: "#fff" }}
          >
            The AI operating system for SaaS finance teams.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed md:text-xl" style={{ color: "#94a3b8" }}>
            SMPL connects pipeline, ARR, revenue, cash, headcount, and financial statements into one
            intelligent operating model so leaders can understand performance, forecast with confidence,
            and make better decisions faster.
          </p>
          <div className="mt-9 flex flex-wrap gap-4">
            <Link
              href={BOOK_DEMO_URL}
              className="inline-flex h-12 items-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-7 text-base font-semibold shadow-lg shadow-teal-500/25 transition hover:brightness-110"
              style={{ color: "#020617" }}
            >
              Book a demo <ArrowRight size={18} />
            </Link>
            <Link
              href="/board"
              className="inline-flex h-12 items-center gap-2 rounded-full border border-white/15 bg-white/5 px-7 text-base font-medium backdrop-blur-sm transition hover:bg-white/10"
              style={{ color: "#fff" }}
            >
              View sample dashboard
            </Link>
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-4 rounded-[2.5rem] bg-gradient-to-br from-teal-500/20 via-violet-500/10 to-cyan-500/20 blur-2xl" />
          <div
            className="relative overflow-hidden rounded-[2rem] border shadow-2xl shadow-black/50 backdrop-blur-xl"
            style={{
              borderColor: "rgba(255,255,255,0.1)",
              background: "rgba(15, 23, 42, 0.92)",
            }}
          >
            <div className="border-b px-6 py-4" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest" style={{ color: "#64748b" }}>
                    Live operating view
                  </p>
                  <h3 className="text-lg font-semibold" style={{ color: "#fff" }}>
                    May 2026 · Executive Summary
                  </h3>
                </div>
                <span
                  className="rounded-full border px-3 py-1 text-xs font-medium"
                  style={{
                    borderColor: "rgba(52, 211, 153, 0.3)",
                    background: "rgba(52, 211, 153, 0.1)",
                    color: "#6ee7b7",
                  }}
                >
                  Validated
                </span>
              </div>
            </div>
            <div className="p-6 pt-5">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {KPIS.map((kpi) => (
                  <div
                    key={kpi.label}
                    className="rounded-2xl border p-4 backdrop-blur-md"
                    style={{
                      borderColor: "rgba(255,255,255,0.1)",
                      background: "rgba(15, 23, 42, 0.85)",
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p
                        className="text-[10px] font-medium uppercase tracking-wider"
                        style={{ color: "#64748b" }}
                      >
                        {kpi.label}
                      </p>
                      <svg viewBox="0 0 64 28" className="h-7 w-16 shrink-0 opacity-80" aria-hidden>
                        <path
                          d={sparklinePath(kpi.spark)}
                          fill="none"
                          stroke={kpi.color}
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>
                    <p
                      className="mt-1.5 text-xl font-semibold tabular-nums sm:text-2xl"
                      style={{ color: "#fff" }}
                    >
                      {kpi.value}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: kpi.accent }}>
                      {kpi.delta}
                    </p>
                  </div>
                ))}
              </div>
              <div
                className="mt-4 rounded-2xl border p-5"
                style={{
                  borderColor: "rgba(20, 184, 166, 0.2)",
                  background: "linear-gradient(to bottom right, rgba(4, 47, 46, 0.85), rgba(15, 23, 42, 0.85))",
                }}
              >
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles size={16} style={{ color: "#2dd4bf" }} />
                  <span className="text-sm font-medium" style={{ color: "#fff" }}>
                    AI commentary
                  </span>
                </div>
                <p className="text-sm leading-relaxed" style={{ color: "#cbd5e1" }}>
                  {HERO_COMMENTARY}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
