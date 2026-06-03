import { ShieldCheck } from "lucide-react";

import { TRUST_CHECKS } from "../constants";
import { SectionReveal } from "../motion";

export function TrustSection() {
  return (
    <section id="trust" className="border-t border-white/10 bg-slate-950 px-6 py-20 md:py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal className="mx-auto max-w-3xl text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-500/15 text-teal-400">
            <ShieldCheck size={24} />
          </div>
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">
            Governed intelligence
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Validation before narrative.
          </h2>
          <p className="mt-4 text-lg text-slate-400">
            Every insight ties back to reconciled models — so executives trust the numbers before
            they trust the words.
          </p>
        </SectionReveal>

        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TRUST_CHECKS.map((check) => (
            <div
              key={check}
              className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-5"
            >
              <ShieldCheck className="mt-0.5 shrink-0 text-teal-400" size={18} />
              <p className="text-sm leading-relaxed text-slate-300">{check}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
