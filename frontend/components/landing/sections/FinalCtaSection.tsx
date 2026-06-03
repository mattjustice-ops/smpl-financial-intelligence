import Link from "next/link";
import { ArrowRight, CalendarClock, Mail } from "lucide-react";

import { SALES_INQUIRY_MAILTO, SCHEDULING_URL } from "../constants";
import { SectionReveal, GlowOrb } from "../motion";

export function FinalCtaSection() {
  return (
    <section id="demo" className="relative overflow-hidden bg-slate-950 px-6 py-28">
      <GlowOrb className="left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 bg-violet-600/20" />
      <div className="relative mx-auto max-w-4xl">
        <SectionReveal className="rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.02] p-10 text-center shadow-2xl backdrop-blur-xl md:p-14">
          <h2 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Turn your SaaS operating data into executive decisions.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-lg text-slate-400">
            Walk through the May 2026 board package or book time with our team to see how SMPL
            connects your stack into one intelligent operating model.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href={SCHEDULING_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-8 text-base font-semibold text-slate-950 shadow-lg shadow-teal-500/20 hover:brightness-110"
            >
              <CalendarClock size={18} />
              Book a demo
            </a>
            <Link
              href="/request-quote"
              className="inline-flex h-12 items-center justify-center rounded-full border border-cyan-400/70 px-8 text-base font-medium text-teal-300 transition hover:border-cyan-300 hover:bg-teal-400/10"
            >
              Request a quote
            </Link>
            <Link
              href="/board"
              className="inline-flex h-12 items-center gap-2 rounded-full border border-white/20 bg-white/5 px-8 text-base font-medium text-white hover:bg-white/10"
            >
              View sample dashboard
              <ArrowRight size={18} />
            </Link>
          </div>
          <a
            href={SALES_INQUIRY_MAILTO}
            className="mt-6 inline-flex items-center gap-2 text-sm text-slate-500 transition hover:text-slate-300"
          >
            <Mail size={16} />
            Contact us
          </a>
        </SectionReveal>
      </div>
    </section>
  );
}
