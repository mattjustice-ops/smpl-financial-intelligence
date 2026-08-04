import { SITE_NAME, SITE_URL } from "@/lib/site";

type BlogPostingJsonLdProps = {
  title: string;
  description: string;
  url: string;
  datePublished?: string | null;
  dateModified?: string | null;
  imageUrl?: string | null;
  authorName?: string | null;
};

/** Article schema so Google has an explicit self-URL beyond link rel=canonical. */
export function BlogPostingJsonLd({
  title,
  description,
  url,
  datePublished,
  dateModified,
  imageUrl,
  authorName,
}: BlogPostingJsonLdProps) {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: title,
    description,
    url,
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": url,
    },
    isPartOf: {
      "@type": "Blog",
      "@id": `${SITE_URL}/blog`,
      name: `${SITE_NAME} Blog`,
      url: `${SITE_URL}/blog`,
    },
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL,
    },
  };

  if (datePublished) jsonLd.datePublished = datePublished;
  if (dateModified || datePublished) {
    jsonLd.dateModified = dateModified || datePublished;
  }
  if (imageUrl) {
    jsonLd.image = [imageUrl];
  }
  if (authorName) {
    jsonLd.author = {
      "@type": "Person",
      name: authorName,
    };
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
