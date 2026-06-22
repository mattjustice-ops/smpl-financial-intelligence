"use client";

import Link from "next/link";
import { CalendarClock, LogIn, Sparkles } from "lucide-react";

import { BOOK_DEMO_URL } from "./constants";

const SECTION_NAV = [
  { hash: "sources", label: "Data layer" },
  { hash: "model", label: "Operating model" },
  { hash: "understand", label: "Insights" },
  { hash: "modules", label: "Platform" },
  { hash: "copilot", label: "AI Copilot" },
] as const;

const navLinkClass =
  "text-sm text-slate-400 transition hover:text-white whitespace-nowrap";

export function LandingHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/70 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-[96rem] items-center justify-between gap-4 px-5 py-3 sm:px-8 sm:py-4 lg:px-10">
        <div className="flex min-w-0 items-center gap-5 lg:gap-6">
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 text-slate-950 shadow-lg shadow-teal-500/25">
              <Sparkles size={18} />
            </div>
            <span className="text-lg font-semibold tracking-tight text-white sm:text-xl">SMPL.ai</span>
          </Link>

          <nav
            className="hidden shrink-0 items-center gap-x-4 lg:flex xl:gap-x-6"
            aria-label="Page sections"
          >
            {SECTION_NAV.map((item) => (
              <Link
                key={item.hash}
                href={{ pathname: "/", hash: item.hash }}
                className={navLinkClass}
              >
                {item.label}
              </Link>
            ))}
            <Link href="/pricing" className={navLinkClass}>
              Pricing
            </Link>
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-2.5">
          <div className="hidden items-center gap-2 sm:flex">
            <Link
              href={BOOK_DEMO_URL}
              className="inline-flex h-9 items-center gap-1.5 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-4 text-xs font-semibold text-slate-950 shadow-lg shadow-teal-500/20 transition hover:brightness-110 sm:h-10 sm:gap-2 sm:px-5 sm:text-sm"
            >
              <CalendarClock size={16} className="hidden sm:block" />
              Book a demo
            </Link>
            <Link
              href="/request-quote"
              className="inline-flex h-9 items-center justify-center rounded-full border border-cyan-400/70 px-4 text-xs font-medium text-teal-300 transition hover:border-cyan-300 hover:bg-teal-400/10 sm:h-10 sm:px-5 sm:text-sm"
            >
              Request a quote
            </Link>
          </div>
          <Link
            href="/board"
            className="inline-flex h-9 items-center justify-center rounded-full border border-white/15 px-3 text-xs font-medium text-white transition hover:bg-white/5 sm:h-10 sm:px-5 sm:text-sm"
          >
            <span className="hidden 2xl:inline">View sample dashboard</span>
            <span className="2xl:hidden">Sample dashboard</span>
          </Link>
          <Link
            href="/login"
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-white/15 px-3 text-xs font-medium text-slate-200 transition hover:bg-white/5 sm:h-10 sm:px-4 sm:text-sm"
          >
            <LogIn size={15} className="hidden sm:block" />
            Log in
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 border-t border-white/5 px-4 py-2 text-center lg:hidden">
        {SECTION_NAV.map((item) => (
          <Link
            key={item.hash}
            href={{ pathname: "/", hash: item.hash }}
            className={`${navLinkClass} text-xs`}
          >
            {item.label}
          </Link>
        ))}
        <Link href="/pricing" className={`${navLinkClass} text-xs`}>
          Pricing
        </Link>
      </div>

      <div className="flex items-center justify-center gap-2 border-t border-white/5 px-4 py-2 sm:hidden">
        <Link
          href={BOOK_DEMO_URL}
          className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-3 text-xs font-semibold text-slate-950"
        >
          <CalendarClock size={14} />
          Book a demo
        </Link>
        <Link
          href="/request-quote"
          className="inline-flex h-9 flex-1 items-center justify-center rounded-full border border-cyan-400/70 px-3 text-xs font-medium text-teal-300"
        >
          Request quote
        </Link>
      </div>
    </header>
  );
}
