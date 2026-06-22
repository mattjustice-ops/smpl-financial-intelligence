import Link from "next/link";
import { CalendarClock, Mail } from "lucide-react";

import { BOOK_DEMO_URL, SALES_EMAIL } from "@/components/landing/constants";

export const metadata = {
  title: "SMPL.ai · Founder",
  description:
    "Matt Justice, founder of SMPL.ai — building the AI operating system for SaaS finance teams.",
};

export default function FounderPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16 sm:py-20">
      <p className="text-sm font-medium uppercase tracking-widest text-teal-400">Founder</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
        Matt Justice
      </h1>
      <p className="mt-2 text-lg text-slate-400">Founder &amp; CEO, SMPL.ai</p>

      <div className="mt-10 space-y-6 text-base leading-relaxed text-slate-300">
        <p>
          I spent years inside SaaS finance teams watching the same pattern repeat: pipeline in one
          place, ARR in another, the three-statement model in spreadsheets, and board prep as a
          fire drill every month. Leaders were making decisions on numbers that didn&apos;t tie.
        </p>
        <p>
          SMPL.ai is the system I wished existed — one governed operating model that connects
          pipeline, ARR, revenue, cash, headcount, and financial statements. When a metric moves,
          you see why. When the board asks a question, you answer from the same source of truth your
          team uses every day.
        </p>
        <p>
          We&apos;re working with growth-stage software companies that want board-ready reporting
          without rebuilding their data stack. If that sounds like your team, I&apos;d love to show
          you what we&apos;ve built.
        </p>
      </div>

      <div className="mt-12 flex flex-col gap-3 sm:flex-row sm:items-center">
        <Link
          href={BOOK_DEMO_URL}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-6 text-sm font-semibold text-slate-950 shadow-lg shadow-teal-500/20 transition hover:brightness-110"
        >
          <CalendarClock size={18} />
          Book a demo
        </Link>
        <a
          href={`mailto:${SALES_EMAIL}?subject=${encodeURIComponent("SMPL.ai — intro")}`}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-white/15 px-6 text-sm font-medium text-slate-200 transition hover:bg-white/5"
        >
          <Mail size={18} />
          {SALES_EMAIL}
        </a>
      </div>

      <div className="mt-16 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          What we&apos;re building
        </h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          <li>Board platform with live warehouse data — ARR, 3-statement model, cash bridge</li>
          <li>Forecast engine with version control and promote-to-final into your data warehouse</li>
          <li>AI commentary and exports built on governed, tie-out validation</li>
        </ul>
        <p className="mt-6 text-sm text-slate-500">
          <Link href="/board" className="text-teal-400 transition hover:text-teal-300">
            View the sample board dashboard
          </Link>
          {" · "}
          <Link href="/" className="text-teal-400 transition hover:text-teal-300">
            Product overview
          </Link>
        </p>
      </div>
    </main>
  );
}
