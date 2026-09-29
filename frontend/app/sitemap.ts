import type { MetadataRoute } from "next";
import type { PortableTextBlock } from "@portabletext/types";

import { sanityFetch } from "@/lib/sanity/client";
import { glossarySlugsQuery, postSlugsQuery } from "@/lib/sanity/queries";
import { isGlossaryTermIndexable } from "@/lib/seo/glossary";
import { SITE_URL } from "@/lib/site";

/**
 * Last content change per static page. Update the date when a page's content changes —
 * crawlers ignore lastmod when it moves on every request.
 */
const STATIC_ROUTES: Array<{ path: string; lastModified: string }> = [
  { path: "", lastModified: "2026-09-23" },
  { path: "/pricing", lastModified: "2026-07-21" },
  { path: "/fpa-software-for-saas", lastModified: "2026-09-29" },
  { path: "/fpa-software-for-lean-finance-teams", lastModified: "2026-09-29" },
  { path: "/saas-board-reporting", lastModified: "2026-09-29" },
  { path: "/arr-revenue-cash-headcount", lastModified: "2026-09-29" },
  { path: "/about", lastModified: "2026-09-24" },
  { path: "/book-demo", lastModified: "2026-07-21" },
  { path: "/request-quote", lastModified: "2026-07-21" },
  { path: "/privacy", lastModified: "2026-08-10" },
];

function toDate(...values: Array<string | null | undefined>): Date | undefined {
  for (const v of values) {
    if (!v) continue;
    const d = new Date(v);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return undefined;
}

function latest(dates: Array<Date | undefined>): Date | undefined {
  const valid = dates.filter((d): d is Date => d instanceof Date);
  return valid.length ? new Date(Math.max(...valid.map((d) => d.getTime()))) : undefined;
}

/** Indexable marketing URLs only — never list noindex / thin stub routes. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = SITE_URL;

  const [posts, terms] = await Promise.all([
    sanityFetch<Array<{ slug: string; publishedAt?: string | null; updatedAt?: string | null }>>(
      postSlugsQuery,
      {},
      [],
    ),
    sanityFetch<Array<{ slug: string; body?: PortableTextBlock[] | null; updatedAt?: string | null }>>(
      glossarySlugsQuery,
      {},
      [],
    ),
  ]);

  const postEntries: MetadataRoute.Sitemap = posts
    .filter((post) => post.slug)
    .map((post) => ({
      url: `${base}/blog/${post.slug}`,
      lastModified: toDate(post.updatedAt, post.publishedAt),
      changeFrequency: "monthly",
      priority: 0.6,
    }));

  // Stub definitions (shortDefinition only) inflate GSC "crawled - not indexed".
  const termEntries: MetadataRoute.Sitemap = terms
    .filter((term) => term.slug && isGlossaryTermIndexable(term.body))
    .map((term) => ({
      url: `${base}/glossary/${term.slug}`,
      lastModified: toDate(term.updatedAt),
      changeFrequency: "monthly",
      priority: 0.5,
    }));

  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map(({ path, lastModified }) => ({
    url: `${base}${path}`,
    lastModified: toDate(lastModified),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.7,
  }));

  const hubEntries: MetadataRoute.Sitemap = [
    {
      url: `${base}/blog`,
      lastModified: latest(postEntries.map((e) => e.lastModified as Date | undefined)),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${base}/glossary`,
      lastModified: latest(termEntries.map((e) => e.lastModified as Date | undefined)),
      changeFrequency: "monthly",
      priority: 0.7,
    },
  ];

  return [...staticEntries, ...hubEntries, ...postEntries, ...termEntries];
}
