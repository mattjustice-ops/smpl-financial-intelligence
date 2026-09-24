import Link from "next/link";

import { SAMPLE_DASHBOARD_URL } from "./constants";

export function LandingFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950 px-6 py-10">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 text-sm text-slate-500 md:flex-row md:items-center">
        <p>
          © 2026 SMPL.ai · FP&A and financial intelligence for SaaS Finance
          teams.
        </p>
        <div className="flex flex-wrap gap-6">
          <Link href="/fpa-software-for-saas" className="transition hover:text-white">
            FP&A for SaaS
          </Link>
          <Link href="/about" className="transition hover:text-white">
            About
          </Link>
          <Link href={SAMPLE_DASHBOARD_URL} className="transition hover:text-white">
            Sample dashboard
          </Link>
          <Link href="/app" className="transition hover:text-white">
            Platform
          </Link>
          <Link href="/privacy" className="transition hover:text-white">
            Privacy
          </Link>
          <Link href={{ pathname: "/", hash: "trust" }} className="transition hover:text-white">
            Trust layer
          </Link>
        </div>
      </div>
    </footer>
  );
}
