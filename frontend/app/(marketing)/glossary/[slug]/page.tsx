import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PortableBody } from "@/components/sanity/PortableBody";
import { isSanityConfigured, sanityFetch } from "@/lib/sanity/client";
import { glossaryBySlugQuery, glossarySlugsQuery } from "@/lib/sanity/queries";
import type { SanityGlossaryTerm } from "@/lib/sanity/types";
import { isGlossaryTermIndexable } from "@/lib/seo/glossary";
import { SITE_NAME, sitePageUrl } from "@/lib/site";

export const revalidate = 60;

type PageProps = { params: { slug: string } };

export async function generateStaticParams() {
  if (!isSanityConfigured()) return [];
  const rows = await sanityFetch<Array<{ slug: string }>>(
    glossarySlugsQuery,
    {},
    [],
  );
  return rows.map((row) => ({ slug: row.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const term = await sanityFetch<SanityGlossaryTerm | null>(
    glossaryBySlugQuery,
    { slug: params.slug },
    null,
  );
  if (!term) {
    return {
      title: { absolute: `Term not found | ${SITE_NAME}` },
      robots: { index: false, follow: false },
    };
  }
  const title = `${term.term} | Glossary | ${SITE_NAME}`;
  const description = term.shortDefinition;
  const url = sitePageUrl(`/glossary/${term.slug}`);
  const indexable = isGlossaryTermIndexable(term.body);
  return {
    title: { absolute: title },
    description,
    alternates: { canonical: url },
    // One-line stubs still render for humans / internal links, but stay out of the index.
    robots: indexable
      ? { index: true, follow: true }
      : { index: false, follow: true },
    openGraph: { title, description, url },
    twitter: { title, description },
  };
}

export default async function GlossaryTermPage({ params }: PageProps) {
  const term = await sanityFetch<SanityGlossaryTerm | null>(
    glossaryBySlugQuery,
    { slug: params.slug },
    null,
  );
  if (!term) notFound();

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Link
        href="/glossary"
        className="text-sm text-slate-400 transition hover:text-teal-300"
      >
        ← Glossary
      </Link>

      <header className="mt-6">
        <h1 className="text-4xl font-semibold tracking-tight text-white md:text-5xl">
          {term.term}
        </h1>
        <p className="mt-4 text-lg text-slate-300">{term.shortDefinition}</p>
      </header>

      <article className="mt-8">
        <PortableBody value={term.body} />
      </article>

      {term.relatedTerms?.length ? (
        <section className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-teal-300">
            Related terms
          </h2>
          <ul className="mt-3 space-y-2">
            {term.relatedTerms.map((related) => (
              <li key={related._id}>
                <Link
                  href={`/glossary/${related.slug}`}
                  className="text-slate-300 transition hover:text-teal-200"
                >
                  {related.term}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {term.relatedPosts?.length ? (
        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-teal-300">
            Related posts
          </h2>
          <ul className="mt-3 space-y-3">
            {term.relatedPosts.map((post) => (
              <li key={post._id}>
                <Link
                  href={`/blog/${post.slug}`}
                  className="font-medium text-white transition hover:text-teal-200"
                >
                  {post.title}
                </Link>
                {post.excerpt ? (
                  <p className="mt-1 text-sm text-slate-500">{post.excerpt}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <aside className="mt-14 rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-6">
        <p className="text-slate-300">
          Want these definitions tied to your live board package?
        </p>
        <Link
          href="/book-demo"
          className="mt-4 inline-flex h-10 items-center rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 text-sm font-semibold text-slate-950"
        >
          Book a demo
        </Link>
      </aside>
    </main>
  );
}
