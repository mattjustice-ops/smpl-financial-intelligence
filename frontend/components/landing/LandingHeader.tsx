"use client";

import Link from "next/link";
import { CalendarClock, Sparkles } from "lucide-react";

import { SCHEDULING_URL } from "./constants";

const NAV = [
  { href: "#sources", label: "Data layer" },
  { href: "#model", label: "Operating model" },
  { href: "#understand", label: "Insights" },
  { href: "#modules", label: "Platform" },
  { href: "#copilot", label: "AI Copilot" },
];

export function LandingHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 text-slate-950 shadow-lg shadow-teal-500/25">
            <Sparkles size={18} />
          </div>
          <span className="text-xl font-semibold tracking-tight text-white">SMPL.ai</span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-slate-400 md:flex">
          {NAV.map((item) => (
            <a key={item.href} href={item.href} className="transition hover:text-white">
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <a
            href={SCHEDULING_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-10 items-center gap-2 rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 text-sm font-semibold text-slate-950 shadow-lg shadow-teal-500/20 transition hover:brightness-110"
          >
            <CalendarClock size={16} />
            Book a demo
          </a>
          <Link
            href="/request-quote"
            className="hidden h-10 items-center justify-center rounded-full border border-cyan-400/70 px-5 text-sm font-medium text-teal-300 transition hover:border-cyan-300 hover:bg-teal-400/10 sm:inline-flex"
          >
            Request a quote
          </Link>
          <Link
            href="/board"
            className="hidden h-10 items-center justify-center rounded-full border border-white/15 px-5 text-sm font-medium text-white transition hover:bg-white/5 md:inline-flex"
          >
            View sample dashboard
          </Link>
        </div>
      </div>
    </header>
  );
}
