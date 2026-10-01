import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { SolutionCards } from "@/components/landing/SolutionPage";
import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

const title = "FP&A Software for SaaS Companies | SMPL.ai";
const description =
  "FP&A software for growing SaaS Finance teams: ARR, revenue, cash, headcount, and financial statements in one governed model for forecasts and board packs.";
const url = sitePageUrl("/fpa-software-for-saas");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const CAPABILITIES = [
  {
    title: "ARR and SaaS metrics",
    body: "Bookings, ARR/MRR, retention, expansion, and waterfall views tied to the same operating model Finance uses for the P&L.",
  },
  {
    title: "Revenue and close",
    body: "Recognized revenue, variance, and management reporting with lineage back to source systems — not a disconnected dashboard layer.",
  },
  {
    title: "Cash and runway",
    body: "Cash forecasting and runway planning that move when hiring, churn, or bookings assumptions change.",
  },
  {
    title: "Headcount and workforce",
    body: "Headcount and compensation planning connected to opex, margin, and cash — so workforce scenarios are not a separate spreadsheet.",
  },
  {
    title: "Forecasting, budgeting, scenarios",
    body: "Driver-based forecasts and an operating budget across the income statement, balance sheet, and cash flow statement, with scenarios that flow through ARR, P&L, and cash together.",
  },
  {
    title: "Plan Assurance",
    body: "The budget tested before approval against prior-year performance, 15 constraints such as cash floors and pipeline coverage, named stress cases, and a simulation of the monthly cash path.",
  },
  {
    title: "Board reporting",
    body: "Board-ready packages with governed numbers, and AI commentary that is checked against the calculated results and traced to the underlying records.",
  },
];

export default function FpaSoftwareForSaasPage() {
  const webPageLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: title,
    url,
    description,
    isPartOf: { "@type": "WebSite", name: "SMPL.ai", url: "https://www.smpl-ai.com/" },
    about: {
      "@type": "SoftwareApplication",
      name: "SMPL.ai",
      applicationCategory: "BusinessApplication",
      applicationSubCategory: "FP&A Software",
      url: "https://www.smpl-ai.com/",
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(webPageLd) }}
      />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-sm font-medium tracking-wide text-teal-300/90">
          SaaS FP&A · Category page
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          FP&A software for SaaS companies
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-slate-300">
          <strong className="font-semibold text-white">
            SMPL.ai is FP&A software for growing SaaS Finance teams.
          </strong>{" "}
          It also represents a broader financial-intelligence approach: one
          governed operating model that connects pipeline, bookings, ARR, GAAP
          revenue, profitability, cash, and workforce — so reporting, forecasting,
          and board packages stay consistent.
        </p>

        <section className="mt-10">
          <h2 className="text-sm font-medium tracking-wide text-slate-400">
            Solutions by need
          </h2>
          <SolutionCards />
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            What SMPL.ai helps Finance teams do
          </h2>
          <p>
            SMPL.ai helps Finance teams with reporting, forecasting, budgeting,
            SaaS metrics, cash planning, scenario analysis, and board reporting.
            It works across ERP, CRM, billing, HRIS, and other financial data
            sources. Deterministic Finance calculations and governed data come
            first; AI is used to analyze and explain results — not to invent the
            numbers.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="text-2xl font-semibold text-white">
            Built around the SaaS operating model
          </h2>
          <ul className="mt-6 space-y-5">
            {CAPABILITIES.map((c) => (
              <li key={c.title} className="border-l border-teal-400/30 pl-4">
                <h3 className="text-base font-semibold text-white">{c.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-400">
                  {c.body}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            ARR, revenue, cash, and headcount together
          </h2>
          <p>
            Many FP&A tools can show an ARR chart, a P&L, and a headcount plan in
            different modules. The harder requirement is one connected model:
            change churn, hiring dates, or new bookings and immediately see the
            effect on ARR, recognized revenue, payroll/opex, EBITDA, cash, and
            runway.
          </p>
          <p>
            That connected SaaS operating model is the core of how SMPL.ai is
            designed — and it is the buyer question where SMPL most clearly
            belongs in the category conversation. See{" "}
            <Link
              href="/arr-revenue-cash-headcount"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              ARR, revenue, cash, and headcount in one financial model
            </Link>
            .
          </p>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            Who it is for
          </h2>
          <p>
            Growing SaaS businesses whose financial and operating data is spread
            across several systems and whose reporting and planning needs have
            become more demanding: board reporting, revenue complexity, workforce
            planning, cash visibility, and forecasts that have to connect. Teams
            that care about ARR methodology, close packages, and implementation
            that does not turn Finance into a second systems-integration
            department.
          </p>
          <p>
            That includes smaller and{" "}
            <Link
              href="/fpa-software-for-lean-finance-teams"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              lean Finance teams
            </Link>{" "}
            without a dedicated systems administrator, established Finance
            organizations that need more capacity, and CFOs who need{" "}
            <Link
              href="/saas-board-reporting"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              board reporting and financial commentary
            </Link>{" "}
            that ties and traces to source. Finance keeps its definitions,
            methodology, and decisions; SMPL provides the connected financial
            foundation.
          </p>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            Implementation led by SMPL
          </h2>
          <p>
            SMPL takes responsibility for implementation: connecting your ERP,
            CRM, billing, and workforce systems, mapping the data, configuring
            the model with your definitions, and reconciling the results to your
            source systems. Your team supplies access, definitions, review, and
            decisions. SMPL works with systems such as{" "}
            <Link href="/integrations/netsuite" className="text-teal-300 underline-offset-2 hover:underline">
              NetSuite
            </Link>
            ,{" "}
            <Link href="/integrations/salesforce" className="text-teal-300 underline-offset-2 hover:underline">
              Salesforce
            </Link>
            ,{" "}
            <Link href="/integrations/maxio" className="text-teal-300 underline-offset-2 hover:underline">
              Maxio
            </Link>
            , Sage Intacct, Xero, and HubSpot; see{" "}
            <Link href="/integrations" className="text-teal-300 underline-offset-2 hover:underline">
              integrations and implementation
            </Link>
            .
          </p>
          <p>
            Once the model is connected, the same numbers feed the budget and{" "}
            <Link
              href="/budgeting-and-plan-assurance"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              Plan Assurance
            </Link>
            , which tests whether the plan can be delivered before it goes to the
            board.
          </p>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            How to evaluate FP&A software for SaaS
          </h2>
          <p>
            Ask vendors to demo one integrated scenario: delay hires, lower new
            ARR, and increase churn — then show resulting ARR, GAAP revenue,
            payroll/opex, EBITDA, cash, and runway by month in the same model.
            Compare that to how explicitly the product is positioned as{" "}
            <em>FP&A software for SaaS</em>, not only as a generic planning
            platform.
          </p>
          <p className="text-sm text-slate-400">
            Related reading:{" "}
            <Link
              href="/blog/best-fpa-software-saas-companies"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              Best FP&A software for SaaS companies
            </Link>
            {" · "}
            <Link
              href="/blog/fpa-software-implementation"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              Why FP&A implementations shouldn&apos;t take months
            </Link>
            {" · "}
            <Link
              href="/platform"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              The SMPL.ai platform
            </Link>
            {" · "}
            <Link
              href="/about"
              className="text-teal-300 underline-offset-2 hover:underline"
            >
              About SMPL.ai
            </Link>
          </p>
        </section>

        <div className="mt-14 flex flex-wrap gap-3">
          <Link
            href="/book-demo"
            className="rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950"
          >
            Book a demo
          </Link>
          <Link
            href="/pricing"
            className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-slate-200 hover:border-teal-400/40"
          >
            View pricing
          </Link>
        </div>
      </main>
      <LandingFooter />
    </>
  );
}
