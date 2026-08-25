import { SITE_DESCRIPTION, SITE_NAME, SITE_URL, siteLogoUrl } from "@/lib/site";

/** Organization schema for Google knowledge panel / logo (Search Console). */
export function OrganizationJsonLd() {
  // Keep dedicated /brand/icon-512.png URL (cache-bust path from SERP fix) but
  // ship the restored pre-SERP smpl-logo.png content there — not regenerated sparkles.
  const logoUrl = siteLogoUrl("/brand/icon-512.png");

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    logo: {
      "@type": "ImageObject",
      url: logoUrl,
      width: 512,
      height: 512,
    },
    description: SITE_DESCRIPTION,
    email: "mattjustice@smpl-ai.com",
    // Populate with real public profiles (LinkedIn company page, X, etc.) when ready.
    // Empty sameAs is worse than omitting — leave unset until URLs are confirmed.
    ...(process.env.NEXT_PUBLIC_ORG_SAME_AS
      ? {
          sameAs: process.env.NEXT_PUBLIC_ORG_SAME_AS.split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }
      : {}),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
