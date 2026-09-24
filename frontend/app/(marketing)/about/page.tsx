import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { sitePageUrl } from "@/lib/site";

const title = "About SMPL.ai | SaaS FP&A & Financial Intelligence";
const description =
  "SMPL.ai is an FP&A and financial intelligence platform built for growing SaaS Finance teams in Portland, Oregon. Founded in 2026 by Matt Justice.";
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
      },
      description:
        "SMPL.ai is an FP&A and financial intelligence platform built for growing SaaS Finance teams.",
      email: "mattjustice@smpl-ai.com",
      sameAs: [
        "https://www.linkedin.com/company/smpl-financial-intelligence",
      ],
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(aboutLd) }}
      />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-sm font-medium tracking-wide text-teal-300/90">
          Company
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          About SMPL.ai
        </h1>

        <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-300">
          <p>
            <strong className="font-semibold text-white">
              SMPL.ai is an FP&A and financial intelligence platform built for
              growing SaaS Finance teams.
            </strong>
          </p>
          <p>
            SMPL.ai helps Finance teams with reporting, forecasting, budgeting,
            SaaS metrics, cash planning, scenario analysis, and board reporting.
          </p>
          <p>
            SMPL.ai works across ERP, CRM, billing, HRIS, and other financial
            data sources. It uses deterministic Finance calculations and
            governed data, with AI used to analyze and explain the results.
          </p>
          <p>
            The product connects pipeline, bookings, ARR, GAAP revenue,
            profitability, cash, and workforce into one operating model — so
            Finance and executives can plan and report without maintaining
            disconnected spreadsheets for each view.
          </p>
        </div>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">Company</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex flex-col gap-1 border-b border-white/10 pb-3 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Legal / brand name</dt>
              <dd className="text-white">SMPL.ai</dd>
            </div>
            <div className="flex flex-col gap-1 border-b border-white/10 pb-3 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Website</dt>
              <dd>
                <a
                  href="https://www.smpl-ai.com/"
                  className="text-teal-300 hover:underline"
                >
                  https://www.smpl-ai.com/
                </a>
              </dd>
            </div>
            <div className="flex flex-col gap-1 border-b border-white/10 pb-3 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Headquarters</dt>
              <dd className="text-white">Portland, Oregon, United States</dd>
            </div>
            <div className="flex flex-col gap-1 border-b border-white/10 pb-3 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Founded</dt>
              <dd className="text-white">2026</dd>
            </div>
            <div className="flex flex-col gap-1 border-b border-white/10 pb-3 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Founder &amp; CEO</dt>
              <dd className="text-white">Matt Justice</dd>
            </div>
            <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
              <dt className="text-slate-500">Contact</dt>
              <dd>
                <a
                  href="mailto:mattjustice@smpl-ai.com"
                  className="text-teal-300 hover:underline"
                >
                  mattjustice@smpl-ai.com
                </a>
              </dd>
            </div>
          </dl>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">Founder</h2>
          <p>
            Matt Justice is founder and CEO of SMPL.ai. He is based in Portland,
            Oregon, and previously held FP&A leadership roles at CARET,
            Schrödinger, and Airship.
          </p>
        </section>

        <section className="mt-12 space-y-4 text-slate-300">
          <h2 className="text-2xl font-semibold text-white">
            What SMPL.ai is not
          </h2>
          <p>
            SMPL.ai is not a replacement for ERP, CRM, or billing systems of
            record. It is the FP&A and financial-intelligence layer that sits on
            top of those systems for SaaS Finance teams.
          </p>
          <p className="text-sm text-slate-500">
            Note: <span className="text-slate-400">smpl.ai</span> (without the
            hyphenated product domain) refers to a different organization. Our
            canonical site is{" "}
            <a
              href="https://www.smpl-ai.com/"
              className="text-teal-300 hover:underline"
            >
              www.smpl-ai.com
            </a>
            .
          </p>
        </section>

        <p className="mt-12 text-sm text-slate-400">
          Product overview:{" "}
          <Link
            href="/fpa-software-for-saas"
            className="text-teal-300 underline-offset-2 hover:underline"
          >
            FP&A software for SaaS companies
          </Link>
          {" · "}
          <Link
            href="/pricing"
            className="text-teal-300 underline-offset-2 hover:underline"
          >
            Pricing
          </Link>
        </p>

        <div className="mt-10">
          <Link
            href="/book-demo"
            className="inline-flex rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950"
          >
            Book a demo
          </Link>
        </div>
      </main>
      <LandingFooter />
    </>
  );
}
