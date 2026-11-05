import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { solutionPageLd, type Faq } from "@/components/landing/SolutionPage";
import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

import { CampfireGets } from "./CampfireGets";

const path = "/integrations/campfire";
const title = "SMPL.ai + Campfire | AI-native finance for your AI-native ERP";
const description =
  "Connect Campfire actuals to your budget, forecast, and board reporting. One financial picture to guide your business.";
const url = sitePageUrl(path);

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE], type: "website", siteName: "SMPL.ai" },
  twitter: { card: "summary_large_image", title, description },
};

const FAQS: Faq[] = [
  {
    q: "Will we need to change our metric definitions?",
    a: "No. We configure your accounts, metrics, and reporting definitions during implementation so the results are familiar to your team.",
  },
  {
    q: "When does the data refresh?",
    a: "Your team starts each refresh when the books close, on your own close calendar. Historical actuals are imported during onboarding.",
  },
  {
    q: "Can we keep our current processes during implementation?",
    a: "Yes. We run alongside your existing processes while mapping, configuration, and validation are completed. Your team reviews the tie-out before go-live.",
  },
  {
    q: "Does SMPL.ai replace Campfire?",
    a: "No. Campfire remains your accounting system. SMPL.ai connects those actuals with the rest of your business data for planning, financial analysis, and management reporting.",
  },
];

function Pill({ children }: { children: string }) {
  return (
    <span className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-slate-200">{children}</span>
  );
}

function CampfireMark() {
  return (
    <span className="inline-flex items-center gap-3">
      <svg viewBox="0 0 48 48" className="h-9 w-9" aria-hidden>
        <path d="M24 8 L24 26" stroke="#f27d26" strokeWidth="4.5" strokeLinecap="round" />
        <path d="M24 26 L8 38" stroke="#f27d26" strokeWidth="4.5" strokeLinecap="round" />
        <path d="M24 26 L40 38" stroke="#f27d26" strokeWidth="4.5" strokeLinecap="round" />
      </svg>
      <span className="text-3xl font-semibold tracking-tight text-[#14352c]">campfire</span>
    </span>
  );
}

function SmplMark() {
  return (
    <span className="inline-flex items-center gap-3">
      <img src="/brand/smpl-logo.png" alt="" className="h-12 w-12 rounded-2xl" />
      <span className="text-3xl font-semibold tracking-tight text-slate-950">
        SMPL<span className="text-teal-500">.ai</span>
      </span>
    </span>
  );
}

export default function CampfireIntegrationPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(solutionPageLd({ title, url, description, faqs: FAQS, crumb: "Campfire", category: { href: "/integrations", label: "Integrations" } })) }}
      />
      <main>
        <section className="mx-auto max-w-6xl px-6 pb-8 pt-16">
          <nav aria-label="Breadcrumb" className="text-sm font-medium tracking-wide">
            <Link href="/integrations" className="text-teal-300/90 hover:text-teal-200">
              Integrations
            </Link>
            <span className="mx-2 text-slate-600">/</span>
            <span className="text-slate-400">Campfire</span>
          </nav>

          <p className="mt-10 text-sm font-semibold tracking-[0.18em] text-teal-300">SMPL.AI + CAMPFIRE</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight text-white md:text-6xl md:leading-[1.05]">
            An AI-native finance platform that{" "}
            <span className="text-teal-300">keeps up with your AI-native ERP.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-300">
            Connect Campfire actuals to your budget, forecast, and board reporting. One financial picture to guide your business.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/book-demo"
              className="rounded-xl bg-teal-400 px-5 py-3 text-sm font-semibold text-slate-950"
            >
              See it in action →
            </Link>
            <a
              href="#cycle"
              className="rounded-xl border border-white/20 px-5 py-3 text-sm text-white hover:border-teal-400/50"
            >
              Explore the integration ↓
            </a>
          </div>
          <p className="mt-6 text-sm text-slate-400">SMPL-led implementation. Your definitions. Your close calendar.</p>
        </section>

        <section id="cycle" className="mx-auto max-w-6xl px-6 py-8">
          <div className="rounded-3xl border border-white/10 bg-[#0c1424] p-6 md:p-8">
            <p className="text-center text-xs font-medium tracking-[0.22em] text-slate-400">
              ONE CONNECTED ACCOUNTING + FINANCE CYCLE
            </p>
            <div className="mt-8 grid gap-8 md:grid-cols-2 md:gap-0">
              <div className="md:border-r md:border-white/10 md:pr-10">
                <div className="flex h-28 items-center justify-center rounded-2xl bg-white">
                  <CampfireMark />
                </div>
                <p className="mt-8 text-xs font-medium tracking-[0.2em] text-slate-400">DAYS</p>
                <p className="text-5xl font-semibold tracking-tight text-orange-500">1–3</p>
                <h2 className="mt-4 text-2xl font-semibold text-white">Close in Campfire</h2>
                <p className="mt-2 text-slate-300">Accounting actuals establish the financial foundation.</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Pill>General ledger</Pill>
                  <Pill>Balance sheet</Pill>
                  <Pill>Cash activity</Pill>
                </div>
              </div>
              <div className="md:pl-10">
                <div className="flex h-28 items-center justify-center rounded-2xl bg-white">
                  <SmplMark />
                </div>
                <p className="mt-8 text-xs font-medium tracking-[0.2em] text-slate-400">DAY</p>
                <p className="text-5xl font-semibold tracking-tight text-teal-300">4</p>
                <h2 className="mt-4 text-2xl font-semibold text-white">Report and plan in SMPL.ai</h2>
                <p className="mt-2 text-slate-300">Connect performance, commentary, and what comes next.</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Pill>Management reporting</Pill>
                  <Pill>Forecasts</Pill>
                  <Pill>Board package</Pill>
                </div>
              </div>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 border-t border-white/10 pt-4 text-sm text-slate-300">
              <span>✓ Read-only connection</span>
              <span>✓ Source-backed reporting</span>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-16">
          <p className="text-center text-xs font-semibold tracking-[0.18em] text-teal-300">WHY SMPL.AI + CAMPFIRE?</p>
          <h2 className="mx-auto mt-4 max-w-3xl text-center text-3xl font-semibold tracking-tight text-white md:text-5xl">
            A month of accounting and finance work. Done in less than one week.
          </h2>
          <p className="mx-auto mt-6 max-w-3xl text-center text-lg text-slate-300">
            Campfire accelerates the close. SMPL.ai brings those results together with the rest of your business data, giving finance more time to understand performance and act on it.
          </p>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            <article>
              <p className="text-xs font-semibold tracking-[0.16em] text-teal-300">01 / REPORT</p>
              <h3 className="mt-3 text-xl font-semibold text-white">Close the books in three days. Finish reporting on the fourth.</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">
                Turn closed books into financial reports, variance commentary, updated forecasts, and board-ready reporting without rebuilding the monthly package by hand.
              </p>
            </article>
            <article>
              <p className="text-xs font-semibold tracking-[0.16em] text-teal-300">02 / CONNECT</p>
              <h3 className="mt-3 text-xl font-semibold text-white">Know what changed. Know what to do about it.</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">
                Connect your financial results with pipeline, subscriptions, and headcount. Understand the drivers and see how revenue and hiring decisions affect cash.
              </p>
            </article>
            <article>
              <p className="text-xs font-semibold tracking-[0.16em] text-teal-300">03 / IMPLEMENT</p>
              <h3 className="mt-3 text-xl font-semibold text-white">Implementation in days, not weeks or months.</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">
                We handle the mapping, configuration, and validation while running alongside your current processes.
              </p>
            </article>
          </div>
          <p className="mt-10 text-center text-slate-300">Your accounts, your metrics, your definitions, reporting you recognize.</p>
        </section>

        <section id="details" className="mx-auto max-w-6xl px-6 py-8">
          <p className="text-xs font-semibold tracking-[0.18em] text-teal-300">WHAT YOU GET</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Your books connect to the rest of the business.
          </h2>
          <p className="mt-4 max-w-3xl text-lg text-slate-300">
            Campfire remains the system of record for your accounting. SMPL.ai uses those actuals to connect planning, operational performance, and reporting in one model.
          </p>
          <div className="mt-10">
            <CampfireGets />
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-16">
          <p className="text-xs font-semibold tracking-[0.18em] text-teal-300">HOW IT WORKS</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-white md:text-5xl">
            A straightforward transition. A familiar financial picture.
          </h2>
          <p className="mt-4 max-w-3xl text-lg text-slate-300">
            SMPL leads the implementation and runs alongside your existing processes. Your team reviews the results before making the switch.
          </p>
          <ol className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              ["01 · CONNECT & MAP", "Start with your books.", "Connect Campfire and map the chart of accounts, entities, and departments into your SMPL.ai model."],
              ["02 · VALIDATE TOGETHER", "Make sure the numbers tie.", "Import historical actuals, review the tie-out to Campfire, and confirm your reporting definitions before go-live."],
              ["03 · REFRESH & REPORT", "Follow your close calendar.", "Start each refresh when the books close. Use the actuals for budget comparisons, forecast updates, and monthly reporting."],
            ].map(([kicker, heading, body]) => (
              <li key={kicker} className="rounded-2xl border border-white/10 p-5">
                <p className="text-xs font-semibold tracking-[0.14em] text-teal-300">{kicker}</p>
                <h3 className="mt-3 text-xl font-semibold text-white">{heading}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
              </li>
            ))}
          </ol>
          <p className="mt-8 max-w-3xl text-slate-300">
            Your ledger stays in Campfire. SMPL.ai reads the data needed for planning and reporting. No journal entries or other changes are posted back.
          </p>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-8">
          <p className="text-xs font-semibold tracking-[0.18em] text-teal-300">A FEW USEFUL DETAILS</p>
          <h2 className="mt-3 text-3xl font-semibold text-white">Before you connect.</h2>
          <dl className="mt-8 divide-y divide-white/10">
            {FAQS.map((f) => (
              <div key={f.q} className="py-5">
                <dt className="font-semibold text-white">{f.q}</dt>
                <dd className="mt-2 text-slate-400">{f.a}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-16 text-center">
          <h2 className="text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Give your finance team more time for the business.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-300">
            See how SMPL.ai + Campfire connect your close, reporting, and financial plan.
          </p>
          <Link
            href="/book-demo"
            className="mt-8 inline-block rounded-xl bg-teal-400 px-5 py-3 text-sm font-semibold text-slate-950"
          >
            Book a walkthrough →
          </Link>
          <p className="mx-auto mt-10 max-w-3xl text-xs leading-relaxed text-slate-500">
            SMPL and Campfire are partners. Campfire is a trademark of its owner. Salesforce, HubSpot, Stripe, and other product names are trademarks of their owners and are used only to identify systems SMPL works with.
          </p>
        </section>
      </main>
      <LandingFooter />
    </>
  );
}
