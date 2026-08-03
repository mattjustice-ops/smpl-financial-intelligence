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
    sameAs: [] as string[],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
