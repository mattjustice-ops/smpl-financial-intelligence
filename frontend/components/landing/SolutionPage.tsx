import Link from "next/link";
import type { ReactNode } from "react";

import { LandingFooter } from "./LandingFooter";

export type Faq = { q: string; a: string };
export type RelatedLink = { href: string; label: string };

export function solutionPageLd({
  title,
  url,
  description,
  faqs,
}: {
  title: string;
  url: string;
  description: string;
  faqs: Faq[];
}) {
  return [
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
  eyebrow,
  h1,
  lead,
  ld,
  children,
  faqs,
  related,
}: {
  eyebrow: string;
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
        <p className="text-sm font-medium tracking-wide text-teal-300/90">{eyebrow}</p>
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
