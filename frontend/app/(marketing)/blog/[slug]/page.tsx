import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { BlogShareControls } from "@/components/blog/BlogShareControls";
import { BlogTableOfContents } from "@/components/blog/BlogTableOfContents";
import { PortableBody } from "@/components/sanity/PortableBody";
import { isSanityConfigured, sanityFetch } from "@/lib/sanity/client";
import { extractPortableHeadings } from "@/lib/sanity/headings";
import { urlForImage } from "@/lib/sanity/image";
import { postBySlugQuery, postSlugsQuery } from "@/lib/sanity/queries";
import type { SanityPost } from "@/lib/sanity/types";
import { SITE_NAME, sitePageUrl } from "@/lib/site";

export const revalidate = 60;

type PageProps = { params: { slug: string } };

export async function generateStaticParams() {
  if (!isSanityConfigured()) return [];
  const rows = await sanityFetch<Array<{ slug: string }>>(postSlugsQuery, {}, []);
  return rows.map((row) => ({ slug: row.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const post = await sanityFetch<SanityPost | null>(
    postBySlugQuery,
    { slug: params.slug },
    null,
  );
  if (!post) {
    return { title: { absolute: `Post not found | ${SITE_NAME}` } };
  }
  const title = post.seoTitle?.trim() || `${post.title} | ${SITE_NAME}`;
  const description =
    post.seoDescription?.trim() ||
    post.excerpt?.trim() ||
    `Read ${post.title} on ${SITE_NAME}.`;
  const url = sitePageUrl(`/blog/${post.slug}`);
  const imageUrl = urlForImage(post.mainImage)?.width(1200).height(630).url();

  return {
    title: { absolute: title },
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: "article",
      images: imageUrl ? [{ url: imageUrl }] : undefined,
    },
    twitter: {
      title,
      description,
      images: imageUrl ? [imageUrl] : undefined,
    },
  };
}

function formatDate(value?: string | null) {
  if (!value) return null;
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return null;
  }
}

export default async function BlogPostPage({ params }: PageProps) {
  const post = await sanityFetch<SanityPost | null>(
    postBySlugQuery,
    { slug: params.slug },
    null,
  );
  if (!post) notFound();

  const date = formatDate(post.publishedAt);
  const imageUrl = urlForImage(post.mainImage)?.width(1400).height(788).url();
  const pageUrl = sitePageUrl(`/blog/${post.slug}`);
  const headings = extractPortableHeadings(post.body);
  const hasToc = headings.length > 0;

  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <div className="max-w-3xl">
        <Link
          href="/blog"
          className="text-sm text-slate-400 transition hover:text-teal-300"
        >
          ← Blog
        </Link>

        <header className="mt-6">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            {date ? (
              <time dateTime={post.publishedAt || undefined}>{date}</time>
            ) : null}
            {post.categories?.map((cat) => (
              <span key={cat.slug} className="text-teal-300/80">
                {cat.title}
              </span>
            ))}
          </div>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white md:text-5xl">
            {post.title}
          </h1>
          {post.excerpt ? (
            <p className="mt-4 text-lg text-slate-400">{post.excerpt}</p>
          ) : null}
          {post.author?.name ? (
            <p className="mt-4 text-sm text-slate-500">
              {post.author.name}
              {post.author.role ? ` · ${post.author.role}` : ""}
            </p>
          ) : null}
        </header>

        <div className="mt-6">
          <BlogShareControls title={post.title} url={pageUrl} />
        </div>
      </div>

      {imageUrl ? (
        <div className="mt-8 max-w-3xl overflow-hidden rounded-2xl border border-white/10">
          <Image
            src={imageUrl}
            alt={post.mainImage?.alt || post.title}
            width={1400}
            height={788}
            className="h-auto w-full object-cover"
            priority
          />
        </div>
      ) : null}

      <div
        className={
          hasToc
            ? "mt-10 lg:grid lg:grid-cols-[minmax(0,42rem)_14rem] lg:items-start lg:justify-between lg:gap-12"
            : "mt-10 max-w-3xl"
        }
      >
        {hasToc ? (
          <div className="order-1 lg:order-2">
            <BlogTableOfContents headings={headings} />
          </div>
        ) : null}

        <article className={hasToc ? "order-2 max-w-3xl lg:order-1" : undefined}>
          <PortableBody value={post.body} headingAnchors />
        </article>
      </div>

      <aside className="mt-14 max-w-3xl rounded-2xl border border-teal-400/20 bg-teal-400/5 px-6 py-6">
        <p className="text-sm font-medium text-teal-200">See it in your close</p>
        <p className="mt-2 text-slate-300">
          Walk through Load → Validate → Lock → Freeze with your own numbers.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/book-demo"
            className="inline-flex h-10 items-center rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-5 text-sm font-semibold text-slate-950"
          >
            Book a demo
          </Link>
          <Link
            href="/request-quote"
            className="inline-flex h-10 items-center rounded-full border border-cyan-400/70 px-5 text-sm font-medium text-teal-300"
          >
            Request a quote
          </Link>
        </div>
      </aside>
    </main>
  );
}
