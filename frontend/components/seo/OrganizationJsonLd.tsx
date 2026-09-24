import { SITE_DESCRIPTION, SITE_NAME, SITE_URL, siteLogoUrl } from "@/lib/site";

/** Organization schema for Google knowledge panel / logo (Search Console). */
export function OrganizationJsonLd() {
  // Keep dedicated /brand/icon-512.png URL (cache-bust path from SERP fix) but
  // ship the restored pre-SERP smpl-logo.png content there — not regenerated sparkles.
  const logoUrl = siteLogoUrl("/brand/icon-512.png");

  const orgDescription =
    "SMPL.ai is an FP&A and financial intelligence platform built for growing SaaS Finance teams. It helps with reporting, forecasting, budgeting, SaaS metrics, cash planning, scenario analysis, and board reporting across ERP, CRM, billing, HRIS, and other financial data sources.";

  const organization = {
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
    description: orgDescription,
    email: "mattjustice@smpl-ai.com",
    sameAs: [
      "https://www.linkedin.com/company/smpl-financial-intelligence",
      ...(process.env.NEXT_PUBLIC_ORG_SAME_AS
        ? process.env.NEXT_PUBLIC_ORG_SAME_AS.split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : []),
    ],
  };

  const software = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: SITE_NAME,
    applicationCategory: "BusinessApplication",
    applicationSubCategory: "FP&A Software",
    operatingSystem: "Web",
    url: SITE_URL,
    description: orgDescription || SITE_DESCRIPTION,
    offers: {
      "@type": "Offer",
      url: `${SITE_URL}/pricing`,
      availability: "https://schema.org/InStock",
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(software) }}
      />
    </>
  );
}
