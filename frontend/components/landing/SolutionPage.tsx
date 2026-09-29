import Link from "next/link";
import type { ReactNode } from "react";

import { LandingFooter } from "./LandingFooter";

export type Faq = { q: string; a: string };
export type RelatedLink = { href: string; label: string };

export const SOLUTIONS = [
  {
    href: "/fpa-software-for-lean-finance-teams",
    label: "Lean Finance teams",
    body: "For SaaS Finance teams of two to five people without a dedicated systems administrator.",
  },
  {
    href: "/saas-board-reporting",
    label: "Board reporting & commentary",
    body: "From close to board package, with commentary grounded in calculated results and traceable to source.",
  },
  {
    href: "/arr-revenue-cash-headcount",
    label: "ARR, revenue, cash & headcount",
    body: "One connected model, so a change in bookings, churn, or hiring flows through every number.",
  },
] as const;

const CATEGORY = { href: "/fpa-software-for-saas", label: "FP&A for SaaS" };

export function solutionPageLd({
  title,
  url,
  description,
  faqs,
  crumb,
}: {
  title: string;
  url: string;
  description: string;
  faqs: Faq[];
  crumb: string;
}) {
  return [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "SMPL.ai", item: "https://www.smpl-ai.com/" },
        {
          "@type": "ListItem",
          position: 2,
          name: CATEGORY.label,
          item: `https://www.smpl-ai.com${CATEGORY.href}`,
        },
        { "@type": "ListItem", position: 3, name: crumb, item: url },
      ],
    },
    {
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
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqs.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  ];
}

export function SolutionPage({
  crumb,
  h1,
  lead,
  ld,
  children,
  faqs,
  related,
}: {
  crumb: string;
  h1: string;
  lead: ReactNode;
  ld: object[];
  children: ReactNode;
  faqs: Faq[];
  related: RelatedLink[];
}) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
      />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <nav aria-label="Breadcrumb" className="text-sm font-medium tracking-wide">
          <Link href={CATEGORY.href} className="text-teal-300/90 hover:text-teal-200">
            {CATEGORY.label}
          </Link>
          <span className="mx-2 text-slate-600">›</span>
          <span className="text-slate-400">{crumb}</span>
        </nav>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          {h1}
        </h1>
        <div className="mt-6 text-lg leading-relaxed text-slate-300">{lead}</div>

        {children}

        <Section title="Frequently asked questions">
          <dl className="space-y-6">
            {faqs.map((f) => (
              <div key={f.q}>
                <dt className="font-semibold text-white">{f.q}</dt>
                <dd className="mt-1 text-slate-400">{f.a}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <OtherSolutions current={crumb} />

        <p className="mt-12 text-sm text-slate-400">
          Related reading:{" "}
          {related.map((r, i) => (
            <span key={r.href}>
              {i > 0 && " · "}
              <Link href={r.href} className="text-teal-300 underline-offset-2 hover:underline">
                {r.label}
              </Link>
            </span>
          ))}
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
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

export function SolutionCards({ items = SOLUTIONS }: { items?: readonly (typeof SOLUTIONS)[number][] }) {
  return (
    <div className={`mt-6 grid gap-4 ${items.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
      {items.map((s) => (
        <Link
          key={s.href}
          href={s.href}
          className="group rounded-xl border border-white/10 bg-white/[0.02] p-4 transition hover:border-teal-400/40 hover:bg-white/[0.04]"
        >
          <span className="block text-sm font-semibold text-white group-hover:text-teal-200">
            {s.label} <span aria-hidden>→</span>
          </span>
          <span className="mt-2 block text-xs leading-relaxed text-slate-400">{s.body}</span>
        </Link>
      ))}
    </div>
  );
}

function OtherSolutions({ current }: { current: string }) {
  return (
    <section className="mt-12">
      <h2 className="text-lg font-semibold text-white">More from FP&A for SaaS</h2>
      <SolutionCards items={SOLUTIONS.filter((s) => s.label !== current)} />
    </section>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-12 space-y-4 text-slate-300">
      <h2 className="text-2xl font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

export function PointList({ items }: { items: { title: string; body: string }[] }) {
  return (
    <ul className="mt-6 space-y-5">
      {items.map((c) => (
        <li key={c.title} className="border-l border-teal-400/30 pl-4">
          <h3 className="text-base font-semibold text-white">{c.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-400">{c.body}</p>
        </li>
      ))}
    </ul>
  );
}
