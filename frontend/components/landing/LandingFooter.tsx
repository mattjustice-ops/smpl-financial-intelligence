import Link from "next/link";

import { SAMPLE_DASHBOARD_URL } from "./constants";

export function LandingFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950 px-6 py-10">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 text-sm text-slate-500 md:flex-row md:items-center">
        <p>© 2026 SMPL.ai · The AI operating system for SaaS finance teams.</p>
        <div className="flex flex-wrap gap-6">
          <Link href={SAMPLE_DASHBOARD_URL} className="transition hover:text-white">
            Sample dashboard
          </Link>
          <Link href="/app" className="transition hover:text-white">
            Platform
          </Link>
          <Link href="/compliance" className="transition hover:text-white">
            SOC 2 readiness
          </Link>
          <a href="#trust" className="transition hover:text-white">
            Trust layer
          </a>
        </div>
      </div>
    </footer>
  );
}
