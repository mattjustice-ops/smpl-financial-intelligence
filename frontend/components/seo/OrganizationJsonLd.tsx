import { SITE_DESCRIPTION, SITE_NAME, SITE_URL, siteLogoUrl } from "@/lib/site";

/** Organization schema for Google knowledge panel / logo (Search Console). */
export function OrganizationJsonLd() {
  const logoUrl = siteLogoUrl("/brand/smpl-logo.png");

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
