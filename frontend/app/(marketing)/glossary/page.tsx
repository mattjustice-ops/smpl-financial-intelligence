import type { Metadata } from "next";
import Link from "next/link";

import { ResourcesEmptyState } from "@/components/sanity/ResourcesEmptyState";
import { sanityFetch } from "@/lib/sanity/client";
import { glossaryListQuery } from "@/lib/sanity/queries";
import type { SanityGlossaryListItem } from "@/lib/sanity/types";
import { SITE_NAME, sitePageUrl } from "@/lib/site";

/** Keep in sync with frontend/sanity/seed/glossary-hub.mjs GLOSSARY_CLUSTERS */
const GLOSSARY_CLUSTERS = [
  {
    id: "arr-recurring",
    title: "ARR & recurring revenue",
    blurb: "How subscription value is defined, bridged, and sourced.",
  },
  {
    id: "retention",
    title: "Retention & churn",
    blurb: "Whether the installed base holds, expands, or erodes.",
  },
  {
    id: "board-close",
    title: "Board reporting & close",
    blurb: "Period lock, narrative, and the package leadership actually reads.",
  },
  {
    id: "forecast",
    title: "Forecast & planning",
    blurb: "Outlook, cash, and scenarios that stay tied to actuals.",
  },
  {
    id: "recognition",
    title: "Recognition & bridges",
    blurb: "GAAP vs operating metrics — and the schedules that connect them.",
  },
  {
    id: "efficiency",
    title: "Efficiency metrics",
    blurb: "Growth spend and cash efficiency — always with the formula stated.",
  },
] as const;

const title = `SaaS Finance Glossary | ${SITE_NAME}`;
const description =
  "SaaS FP&A glossary for board and close: ARR, waterfall, NRR, GRR, billing vs CRM ARR, board packs, cash forecast, and more — definitions finance leaders actually use.";
const url = sitePageUrl("/glossary");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

export const revalidate = 60;

function groupByLetter(terms: SanityGlossaryListItem[]) {
  const map = new Map<string, SanityGlossaryListItem[]>();
  for (const term of terms) {
    const letter = (term.term[0] || "#").toUpperCase();
    const key = /[A-Z]/.test(letter) ? letter : "#";
    const list = map.get(key) || [];
    list.push(term);
    map.set(key, list);
  }
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
}

function TermRow({ item }: { item: SanityGlossaryListItem }) {
  return (
    <li>
      <Link
        href={`/glossary/${item.slug}`}
        className="block py-4 transition hover:bg-white/[0.02]"
      >
        <span className="text-lg font-medium text-white">{item.term}</span>
        <p className="mt-1 text-sm text-slate-400">{item.shortDefinition}</p>
      </Link>
    </li>
  );
}

export default async function GlossaryIndexPage() {
  const terms = await sanityFetch<SanityGlossaryListItem[]>(
    glossaryListQuery,
    {},
    [],
  );
  const groups = groupByLetter(terms);
  const clusteredIds = new Set(GLOSSARY_CLUSTERS.map((c) => c.id));
  const unclustered = terms.filter(
    (t) => !t.cluster || !clusteredIds.has(t.cluster as (typeof GLOSSARY_CLUSTERS)[number]["id"]),
  );

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <div className="max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-300/90">
          Resources
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          SaaS Finance Glossary
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Metric literacy for board, close, and reconciliation — not a billing
          encyclopedia. Each term covers what it is, how it&apos;s calculated,
          where it breaks, and how it shows up in the pack.
        </p>
        {terms.length > 0 ? (
          <nav
            className="mt-6 flex flex-wrap gap-2"
            aria-label="Glossary clusters"
          >
            {GLOSSARY_CLUSTERS.map((cluster) => (
              <a
                key={cluster.id}
                href={`#cluster-${cluster.id}`}
                className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-slate-300 transition hover:border-teal-400/40 hover:text-teal-200"
              >
                {cluster.title}
              </a>
            ))}
            <a
              href="#a-z"
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-slate-300 transition hover:border-teal-400/40 hover:text-teal-200"
            >
              A–Z index
            </a>
          </nav>
        ) : null}
      </div>

      {terms.length === 0 ? (
        <div className="mt-12">
          <ResourcesEmptyState
            title="Glossary coming soon"
            description="Definitions for SaaS finance, close, and board reporting are on the way. Book a demo if you'd like a walkthrough now."
          />
        </div>
      ) : (
        <>
          <div className="mt-14 space-y-14">
            {GLOSSARY_CLUSTERS.map((cluster) => {
              const items = terms.filter((t) => t.cluster === cluster.id);
              if (items.length === 0) return null;
              return (
                <section
                  key={cluster.id}
                  id={`cluster-${cluster.id}`}
                  aria-labelledby={`heading-${cluster.id}`}
                >
                  <h2
                    id={`heading-${cluster.id}`}
                    className="text-2xl font-semibold tracking-tight text-white"
                  >
                    {cluster.title}
                  </h2>
                  <p className="mt-2 text-sm text-slate-400">{cluster.blurb}</p>
                  <ul className="mt-4 divide-y divide-white/5 border-t border-white/10">
                    {items.map((item) => (
                      <TermRow key={item._id} item={item} />
                    ))}
                  </ul>
                </section>
              );
            })}

            {unclustered.length > 0 ? (
              <section id="cluster-other" aria-labelledby="heading-other">
                <h2
                  id="heading-other"
                  className="text-2xl font-semibold tracking-tight text-white"
                >
                  More terms
                </h2>
                <ul className="mt-4 divide-y divide-white/5 border-t border-white/10">
                  {unclustered.map((item) => (
                    <TermRow key={item._id} item={item} />
                  ))}
                </ul>
              </section>
            ) : null}
          </div>

          <div id="a-z" className="mt-20 space-y-10">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-white">
                A–Z index
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                Full list of glossary terms.
              </p>
            </div>
            {groups.map(([letter, items]) => (
              <section key={letter} aria-labelledby={`glossary-${letter}`}>
                <h3
                  id={`glossary-${letter}`}
                  className="border-b border-white/10 pb-2 text-sm font-semibold tracking-widest text-teal-300"
                >
                  {letter}
                </h3>
                <ul className="mt-4 divide-y divide-white/5">
                  {items.map((item) => (
                    <TermRow key={`az-${item._id}`} item={item} />
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
