import type { MetadataRoute } from "next";

import { sanityFetch } from "@/lib/sanity/client";
import { glossarySlugsQuery, postSlugsQuery } from "@/lib/sanity/queries";
import { SITE_URL } from "@/lib/site";

/** Indexable marketing URLs only — never list noindex routes (login, studio, etc.). */
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
    sanityFetch<Array<{ slug: string }>>(postSlugsQuery, {}, []),
    sanityFetch<Array<{ slug: string }>>(glossarySlugsQuery, {}, []),
  ]);

  const entries: MetadataRoute.Sitemap = staticRoutes.map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date(),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.7,
  }));

  for (const post of posts) {
    if (!post.slug) continue;
    entries.push({
      url: `${base}/blog/${post.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.6,
    });
  }

  for (const term of terms) {
    if (!term.slug) continue;
    entries.push({
      url: `${base}/glossary/${term.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    });
  }

  return entries;
}
