import { X, Check } from "lucide-react";

import { SectionReveal } from "../motion";

const BEFORE = [
  "Disconnected spreadsheets and slide decks",
  "Stale board packages rebuilt every month",
  "Manual variance commentary from scratch",
  "Low confidence in forecast and hiring plans",
  "Unclear ownership across Finance, GTM, and HR",
];

const AFTER = [
  "One governed SaaS operating model",
  "Automated executive insights and drivers",
  "ARR, revenue, cash, and headcount connected",
  "Board-ready reporting from live data",
  "Faster decisions with clear recommendations",
];

export function BeforeAfterSection() {
  return (
    <section className="border-y border-white/10 bg-slate-950 px-6 py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-cyan-400">
            The shift
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            From reporting assembly to operating intelligence.
          </h2>
        </SectionReveal>

        <div className="mt-14 grid gap-6 md:grid-cols-2">
          <div className="rounded-[2rem] border border-red-500/20 bg-red-950/20 p-8 md:p-10">
            <p className="text-sm font-semibold uppercase tracking-widest text-red-300/80">
              Before SMPL
            </p>
            <ul className="mt-6 space-y-4">
              {BEFORE.map((item) => (
                <li key={item} className="flex gap-3 text-slate-300">
                  <X className="mt-0.5 shrink-0 text-red-400" size={18} />
                  <span className="text-sm leading-relaxed md:text-base">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[2rem] border border-teal-500/25 bg-gradient-to-br from-teal-950/40 to-violet-950/30 p-8 md:p-10">
            <p className="text-sm font-semibold uppercase tracking-widest text-teal-300">
              After SMPL
            </p>
            <ul className="mt-6 space-y-4">
              {AFTER.map((item) => (
                <li key={item} className="flex gap-3 text-slate-200">
                  <Check className="mt-0.5 shrink-0 text-teal-400" size={18} />
                  <span className="text-sm leading-relaxed md:text-base">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
