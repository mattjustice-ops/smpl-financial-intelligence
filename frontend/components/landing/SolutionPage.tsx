import Link from "next/link";
import type { ReactNode } from "react";

import { LandingFooter } from "./LandingFooter";

export type Faq = { q: string; a: string };
export type RelatedLink = { href: string; label: string };
export type Crumb = { href: string; label: string };
export type SolutionCard = { href: string; label: string; body: string };

export const SOLUTIONS: readonly SolutionCard[] = [
  {
    href: "/fpa-software-for-lean-finance-teams",
    label: "Lean Finance teams",
    body: "For Finance teams that need board reporting and planning without adding a planning systems administrator.",
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
  {
    href: "/budgeting-and-plan-assurance",
    label: "Budgeting & Plan Assurance",
    body: "A driver-based budget across all three statements, tested against constraints and stress cases before it goes to the board.",
  },
  {
    href: "/integrations",
    label: "Integrations & implementation",
    body: "Your ERP, CRM, billing, and workforce data connected by SMPL as part of implementation.",
  },
] as const;

export const FPA_CATEGORY: Crumb = { href: "/fpa-software-for-saas", label: "FP&A for SaaS" };
export const INTEGRATIONS_CATEGORY: Crumb = { href: "/integrations", label: "Integrations" };

const HOME = "https://www.smpl-ai.com";

export function solutionPageLd({
  title,
  url,
  description,
  faqs,
  crumb,
  category = FPA_CATEGORY,
}: {
  title: string;
  url: string;
  description: string;
  faqs: Faq[];
  crumb: string;
  category?: Crumb | null;
}) {
  const trail = [
    { "@type": "ListItem", position: 1, name: "SMPL.ai", item: `${HOME}/` },
    ...(category
      ? [{ "@type": "ListItem", position: 2, name: category.label, item: `${HOME}${category.href}` }]
      : []),
    { "@type": "ListItem", position: category ? 3 : 2, name: crumb, item: url },
  ];
  return [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: trail,
    },
    {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: title,
      url,
      description,
      isPartOf: { "@type": "WebSite", name: "SMPL.ai", url: `${HOME}/` },
      about: {
        "@type": "SoftwareApplication",
        name: "SMPL.ai",
        applicationCategory: "BusinessApplication",
        applicationSubCategory: "FP&A Software",
        operatingSystem: "Web browser",
        url: `${HOME}/`,
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
  category = FPA_CATEGORY,
  more,
  secondaryCta = { href: "/pricing", label: "View pricing" },
  footnote,
}: {
  crumb: string;
  h1: string;
  lead: ReactNode;
  ld: object[];
  children: ReactNode;
  faqs: Faq[];
  related: RelatedLink[];
  category?: Crumb | null;
  more?: { title: string; items: readonly SolutionCard[] };
  secondaryCta?: RelatedLink;
  footnote?: ReactNode;
}) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
      />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <nav aria-label="Breadcrumb" className="text-sm font-medium tracking-wide">
          <Link href={category?.href ?? "/"} className="text-teal-300/90 hover:text-teal-200">
            {category?.label ?? "SMPL.ai"}
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

        {more ? (
          <section className="mt-12">
            <h2 className="text-lg font-semibold text-white">{more.title}</h2>
            <SolutionCards items={more.items} />
          </section>
        ) : (
          <OtherSolutions current={crumb} />
        )}

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
            href={secondaryCta.href}
            className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-slate-200 hover:border-teal-400/40"
          >
            {secondaryCta.label}
          </Link>
        </div>
        {footnote ? (
          <p className="mt-10 text-xs leading-relaxed text-slate-500">{footnote}</p>
        ) : null}
      </main>
      <LandingFooter />
    </>
  );
}

export function SolutionCards({ items = SOLUTIONS }: { items?: readonly SolutionCard[] }) {
  return (
    <div className={`mt-6 grid gap-4 ${items.length === 2 || items.length === 4 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
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

export function Steps({ items }: { items: { title: string; body: string }[] }) {
  return (
    <ol className="mt-6 space-y-5">
      {items.map((c, i) => (
        <li key={c.title} className="flex gap-4">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-teal-400/40 text-xs font-semibold text-teal-200">
            {i + 1}
          </span>
          <div>
            <h3 className="text-base font-semibold text-white">{c.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-slate-400">{c.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
