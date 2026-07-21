import type { Metadata } from "next";
import Link from "next/link";

import { ResourcesEmptyState } from "@/components/sanity/ResourcesEmptyState";
import { isSanityConfigured, sanityFetch } from "@/lib/sanity/client";
import { postsListQuery } from "@/lib/sanity/queries";
import type { SanityPostListItem } from "@/lib/sanity/types";
import { SITE_NAME, sitePageUrl } from "@/lib/site";

const title = `Blog | ${SITE_NAME}`;
const description =
  "Insights on SaaS FP&A, board reporting, close workflow, and AI commentary that finance teams can sign.";
const url = sitePageUrl("/blog");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

export const revalidate = 60;

function formatDate(value?: string | null) {
  if (!value) return null;
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return null;
  }
}

export default async function BlogIndexPage() {
  const posts = await sanityFetch<SanityPostListItem[]>(postsListQuery, {}, []);
  const configured = isSanityConfigured();

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <div className="max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-300/90">
          Resources
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
          Blog
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Evidence-backed close, board packages, and commentary worth signing —
          written for SaaS finance teams.
        </p>
      </div>

      {!configured || posts.length === 0 ? (
        <div className="mt-12">
          <ResourcesEmptyState
            title={configured ? "No posts published yet" : "Blog content coming soon"}
            description={
              configured
                ? "Create and publish posts in Sanity Studio to populate this page."
                : "Sanity is not configured in this environment. Set NEXT_PUBLIC_SANITY_PROJECT_ID to enable the blog."
            }
            hint={
              configured
                ? "Seed starter content with npm run seed:sanity (requires SANITY_API_WRITE_TOKEN)."
                : undefined
            }
          />
        </div>
      ) : (
        <ul className="mt-12 space-y-6">
          {posts.map((post) => {
            const date = formatDate(post.publishedAt);
            return (
              <li key={post._id}>
                <Link
                  href={`/blog/${post.slug}`}
                  className="group block rounded-2xl border border-white/10 bg-white/[0.02] px-6 py-6 transition hover:border-teal-400/30 hover:bg-white/[0.04]"
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                    {date ? <time dateTime={post.publishedAt || undefined}>{date}</time> : null}
                    {post.categories?.map((cat) => (
                      <span key={cat.slug} className="text-teal-300/80">
                        {cat.title}
                      </span>
                    ))}
                  </div>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white transition group-hover:text-teal-200">
                    {post.title}
                  </h2>
                  {post.excerpt ? (
                    <p className="mt-2 text-slate-400">{post.excerpt}</p>
                  ) : null}
                  {post.author?.name ? (
                    <p className="mt-3 text-sm text-slate-500">{post.author.name}</p>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
