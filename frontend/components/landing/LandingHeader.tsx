"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CalendarClock, ChevronDown, LogIn, Sparkles } from "lucide-react";

import { BOOK_DEMO_URL, SAMPLE_DASHBOARD_URL } from "./constants";

const SECTION_NAV = [
  { hash: "sources", label: "Data layer" },
  { hash: "model", label: "Operating model" },
  { hash: "understand", label: "Insights" },
  { hash: "modules", label: "Platform" },
  { hash: "copilot", label: "AI Copilot" },
] as const;

const RESOURCES_LINKS = [
  { href: "/blog", label: "Blog", description: "Close, board packages, commentary" },
  { href: "/glossary", label: "Glossary", description: "SaaS FP&A definitions" },
] as const;

const navLinkClass =
  "text-sm text-slate-400 transition hover:text-white whitespace-nowrap";

export function LandingHeader() {
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const resourcesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!resourcesRef.current?.contains(event.target as Node)) {
        setResourcesOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setResourcesOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

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
            <div className="relative" ref={resourcesRef}>
              <button
                type="button"
                className={`${navLinkClass} inline-flex items-center gap-1`}
                aria-expanded={resourcesOpen}
                aria-haspopup="menu"
                onClick={() => setResourcesOpen((open) => !open)}
              >
                Resources
                <ChevronDown
                  size={14}
                  className={`transition ${resourcesOpen ? "rotate-180" : ""}`}
                />
              </button>
              {resourcesOpen ? (
                <div
                  role="menu"
                  className="absolute left-0 top-full z-50 mt-2 min-w-[14rem] overflow-hidden rounded-xl border border-white/10 bg-slate-950/95 py-1 shadow-xl shadow-black/40 backdrop-blur-xl"
                >
                  {RESOURCES_LINKS.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      role="menuitem"
                      className="block px-4 py-2.5 transition hover:bg-white/5"
                      onClick={() => setResourcesOpen(false)}
                    >
                      <span className="block text-sm text-white">{item.label}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {item.description}
                      </span>
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
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
            href={SAMPLE_DASHBOARD_URL}
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
        <Link href="/blog" className={`${navLinkClass} text-xs`}>
          Blog
        </Link>
        <Link href="/glossary" className={`${navLinkClass} text-xs`}>
          Glossary
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
