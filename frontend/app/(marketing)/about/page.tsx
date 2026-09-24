import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { BOOK_DEMO_URL } from "@/components/landing/constants";
import { sitePageUrl } from "@/lib/site";

const title = "About SMPL.ai | Why we built financial intelligence for SaaS Finance";
const description =
  "SMPL.ai is the AI operating system for SaaS Finance teams. Founded by Matt Justice to give growing companies the financial intelligence of a world-class CFO organization without having to build one.";
const url = sitePageUrl("/about");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: true, follow: true },
  openGraph: { title, description, url, type: "website", siteName: "SMPL.ai" },
  twitter: { title, description },
};

export default function AboutPage() {
  const aboutLd = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: title,
    url,
    description,
    mainEntity: {
      "@type": "Organization",
      name: "SMPL.ai",
      url: "https://www.smpl-ai.com/",
      foundingDate: "2026",
      foundingLocation: {
        "@type": "Place",
        address: {
          "@type": "PostalAddress",
          addressLocality: "Portland",
          addressRegion: "OR",
          addressCountry: "US",
        },
      },
      founder: {
        "@type": "Person",
        name: "Matt Justice",
        jobTitle: "Founder and CEO",
        url: "https://www.linkedin.com/in/matt-justice-a136a14b/",
        sameAs: ["https://www.linkedin.com/in/matt-justice-a136a14b/"],
      },
      description:
        "SMPL.ai is the AI operating system for SaaS Finance teams, built for reporting, forecasting, and planning on connected financial and operating information.",
      email: "mattjustice@smpl-ai.com",
      sameAs: [
        "https://www.linkedin.com/company/smpl-financial-intelligence",
        "https://www.crunchbase.com/organization/smpl-ai",
        "https://app.dealroom.co/companies/smpl_ai_1",
      ],
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutLd) }}
      />
      <main className="px-6 py-16 md:py-20">
        {/* Mission */}
        <section className="mx-auto max-w-3xl">
          <p className="text-sm font-medium tracking-wide text-teal-300/90">
            About SMPL.ai
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-5xl md:leading-[1.15]">
            Every growing SaaS company should be able to operate with the
            financial intelligence of a world-class CFO organization without
            having to build one.
          </h1>
          <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-300">
            <p>
              Financial intelligence means knowing how the business is
              performing, what is driving the results, and what today&apos;s
              decisions mean for growth, hiring, and cash.
            </p>
            <p>
              <strong className="font-semibold text-white">
                SMPL.ai is the AI operating system for SaaS Finance teams.
              </strong>{" "}
              It helps CFOs and Finance leaders with reporting, forecasting, and
              planning so they can understand performance and guide the business
              with more clarity and less assembly work.
            </p>
          </div>
        </section>

        {/* Founder story */}
        <section className="mx-auto mt-20 max-w-3xl border-t border-white/10 pt-16">
          <p className="text-sm font-medium tracking-wide text-teal-300/90">
            Founder
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">
            Matt Justice, Founder &amp; CEO
          </h2>
          <p className="mt-2 text-base text-slate-400">
            Portland, Oregon · Corporate FP&amp;A, strategic and GTM Finance, and
            revenue operations
          </p>
          <div className="mt-8 space-y-5 text-base leading-relaxed text-slate-300 md:text-lg">
            <p>
              I have spent my career inside SaaS Finance: corporate FP&amp;A at
              Airship and Schrödinger, GTM Finance at CARET, and revenue and
              billings operations at Airship. Across those roles I worked the
              same problems growing Finance teams face every month: reporting,
              budgeting, forecasting, SaaS revenue metrics, cash and workforce
              planning, and connecting operational activity to financial
              results.
            </p>
            <p>
              I also worked directly with the systems and processes behind those
              answers: spreadsheets, ERP, CRM, billing data, and planning
              platforms. At Airship I led a team of three across revenue,
              billings, and collections, and implemented automation that cut
              reporting timelines by 95%. Earlier in my career at PGE I managed
              and forecasted a $600 million capital budget. That combination
              matters. I understand both the questions leadership needs answered
              and the work required to assemble reliable answers from systems
              that were never designed to speak the same language.
            </p>
            <p>
              The pattern I kept seeing was simple and expensive. Finance teams
              spend too much capacity collecting information across systems,
              reconciling what does not match, maintaining models, and preparing
              reporting before they can help leadership decide. The opportunity
              I saw was to give growing teams more room to interpret
              performance, evaluate decisions, and guide the business.
            </p>
            <p>
              In 2026 I founded SMPL.ai to make the financial capabilities of a
              world-class CFO organization accessible to growing SaaS companies,
              without requiring them to assemble that entire organization
              themselves.
            </p>
          </div>
        </section>

        {/* How experience shapes the product */}
        <section className="mx-auto mt-20 max-w-3xl border-t border-white/10 pt-16">
          <h2 className="text-3xl font-semibold tracking-tight text-white">
            How that experience shapes SMPL
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-400">
            SMPL works alongside the ERP, CRM, billing, and HR systems Finance
            already trusts. It is the financial intelligence layer on top of
            those systems of record, not a replacement for them.
          </p>
          <div className="mt-10 space-y-10">
            <div>
              <h3 className="text-xl font-semibold text-white">
                Connected financial and operating information
              </h3>
              <p className="mt-3 text-base leading-relaxed text-slate-300">
                Revenue, hiring, and cash decisions need to be understood
                together. When those views live in separate models, Finance
                spends the week reconciling them instead of explaining what
                changed. SMPL is built so the operating story and the financial
                story stay connected.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">
                Numbers Finance can explain and defend
              </h3>
              <p className="mt-3 text-base leading-relaxed text-slate-300">
                Deterministic calculations produce the numbers. AI helps analyze
                and explain results that Finance can validate. That boundary
                matters when a board package, forecast, or variance narrative has
                to stand up to scrutiny.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">
                More capacity to guide the business
              </h3>
              <p className="mt-3 text-base leading-relaxed text-slate-300">
                The goal is not more dashboards. It is less time assembling
                reporting and maintaining disconnected models, and more time
                helping leadership understand performance and decide what to do
                next.
              </p>
            </div>
          </div>
        </section>

        {/* Invitation */}
        <section className="mx-auto mt-24 max-w-3xl border-t border-white/10 pt-20 pb-8 md:mt-28 md:pt-24 md:pb-12">
          <h2 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
            Let&apos;s talk about your Finance challenges
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">
            If your team is spending too much of the close and planning cycle
            assembling information before you can guide the business, I would
            welcome a conversation about what that looks like for you.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link
              href={BOOK_DEMO_URL}
              className="inline-flex rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950"
            >
              Book a demo
            </Link>
            <Link
              href="/fpa-software-for-saas"
              className="inline-flex rounded-full border border-white/15 px-5 py-2.5 text-sm text-slate-200 hover:border-teal-400/40"
            >
              FP&amp;A for SaaS
            </Link>
          </div>
          <p className="mt-14 max-w-xl text-xs leading-relaxed text-slate-500">
            Our site is www.smpl-ai.com. The domain smpl.ai belongs to a
            different organization.
          </p>
        </section>
      </main>
      <LandingFooter />
    </>
  );
}
