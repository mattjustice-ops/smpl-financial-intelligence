import type { Metadata } from "next";
import Link from "next/link";

import { ResourcesEmptyState } from "@/components/sanity/ResourcesEmptyState";
import { isSanityConfigured, sanityFetch } from "@/lib/sanity/client";
import { glossaryListQuery } from "@/lib/sanity/queries";
import type { SanityGlossaryListItem } from "@/lib/sanity/types";
import { SITE_NAME, sitePageUrl } from "@/lib/site";

const title = `Glossary | ${SITE_NAME}`;
const description =
  "SaaS FP&A glossary: ARR, NRR, deferred revenue, waterfall, close, MD&A, freeze pack, and more.";
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

export default async function GlossaryIndexPage() {
  const terms = await sanityFetch<SanityGlossaryListItem[]>(
    glossaryListQuery,
    {},
    [],
  );
  const configured = isSanityConfigured();
  const groups = groupByLetter(terms);

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <div className="max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-300/90">
          Resources
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          Glossary
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Plain-language definitions for SaaS finance, close, and board reporting.
        </p>
      </div>

      {!configured || terms.length === 0 ? (
        <div className="mt-12">
          <ResourcesEmptyState
            title={configured ? "No glossary terms yet" : "Glossary coming soon"}
            description={
              configured
                ? "Add glossary terms in Sanity Studio (or run the seed script) to populate this page."
                : "Sanity is not configured in this environment. Set NEXT_PUBLIC_SANITY_PROJECT_ID to enable the glossary."
            }
          />
        </div>
      ) : (
        <div className="mt-12 space-y-10">
          {groups.map(([letter, items]) => (
            <section key={letter} aria-labelledby={`glossary-${letter}`}>
              <h2
                id={`glossary-${letter}`}
                className="border-b border-white/10 pb-2 text-sm font-semibold tracking-widest text-teal-300"
              >
                {letter}
              </h2>
              <ul className="mt-4 divide-y divide-white/5">
                {items.map((item) => (
                  <li key={item._id}>
                    <Link
                      href={`/glossary/${item.slug}`}
                      className="block py-4 transition hover:bg-white/[0.02]"
                    >
                      <span className="text-lg font-medium text-white">{item.term}</span>
                      <p className="mt-1 text-sm text-slate-400">{item.shortDefinition}</p>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
