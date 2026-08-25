import type { MetadataRoute } from "next";
import type { PortableTextBlock } from "@portabletext/types";

import { sanityFetch } from "@/lib/sanity/client";
import { glossarySlugsQuery, postSlugsQuery } from "@/lib/sanity/queries";
import { isGlossaryTermIndexable } from "@/lib/seo/glossary";
import { SITE_URL } from "@/lib/site";

/** Indexable marketing URLs only — never list noindex / thin stub routes. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = SITE_URL;
  const staticRoutes = [
    "",
    "/pricing",
    "/book-demo",
    "/request-quote",
    "/privacy",
    "/blog",
    "/glossary",
  ];

  const [posts, terms] = await Promise.all([
    sanityFetch<Array<{ slug: string; publishedAt?: string | null }>>(
      postSlugsQuery,
      {},
      [],
    ),
    sanityFetch<Array<{ slug: string; body?: PortableTextBlock[] | null }>>(
      glossarySlugsQuery,
      {},
      [],
    ),
  ]);

  const entries: MetadataRoute.Sitemap = staticRoutes.map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date(),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.7,
  }));

  for (const post of posts) {
    if (!post.slug) continue;
    const lastModified = post.publishedAt
      ? new Date(post.publishedAt)
      : new Date();
    entries.push({
      url: `${base}/blog/${post.slug}`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.6,
    });
  }

  for (const term of terms) {
    if (!term.slug) continue;
    // Stub definitions (shortDefinition only) inflate GSC "crawled - not indexed".
    if (!isGlossaryTermIndexable(term.body)) continue;
    entries.push({
      url: `${base}/glossary/${term.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    });
  }

  return entries;
}
