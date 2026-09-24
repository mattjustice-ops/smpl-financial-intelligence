import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { sitePageUrl } from "@/lib/site";

const title = "FP&A Software for SaaS Companies | SMPL.ai";
const description =
  "SMPL.ai is FP&A software for growing SaaS Finance teams. Connect ARR, revenue, cash, headcount, and financial statements in one governed model for forecasting, reporting, and board packages.";
const url = sitePageUrl("/fpa-software-for-saas");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
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
    body: "Driver-based planning across the SaaS operating model, with scenarios that flow through ARR, P&L, and cash together.",
  },
  {
    title: "Board reporting",
    body: "Board-ready packages with governed numbers and commentary that can be traced to the underlying records.",
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
            belongs in the category conversation.
          </p>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            Who it is for
          </h2>
          <p>
            Growth-stage B2B SaaS companies where Finance needs trusted board
            reporting and planning without standing up a heavy enterprise
            planning stack. Teams that care about ARR methodology, close
            packages, and implementation that does not turn Finance into a
            second systems-integration department.
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
