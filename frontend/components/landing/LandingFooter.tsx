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
          <Link href="/fpa-software-for-lean-finance-teams" className="transition hover:text-white">
            Lean Finance teams
          </Link>
          <Link href="/saas-board-reporting" className="transition hover:text-white">
            Board reporting
          </Link>
          <Link href="/arr-revenue-cash-headcount" className="transition hover:text-white">
            ARR, cash & headcount
          </Link>
          <Link href="/budgeting-and-plan-assurance" className="transition hover:text-white">
            Budgeting & Plan Assurance
          </Link>
          <Link href="/integrations" className="transition hover:text-white">
            Integrations
          </Link>
          <Link href="/integrations/salesforce" className="transition hover:text-white">
            Salesforce
          </Link>
          <Link href="/blog/best-fpa-software-saas-companies" className="transition hover:text-white">
            Buyer&apos;s guide
          </Link>
          <Link href="/about" className="transition hover:text-white">
            About
          </Link>
          <Link href={SAMPLE_DASHBOARD_URL} className="transition hover:text-white">
            Sample dashboard
          </Link>
          <Link href="/platform" className="transition hover:text-white">
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
