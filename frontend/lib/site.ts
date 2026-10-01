/** Canonical marketing site URL (www). Apex redirects to www on Vercel. */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL?.trim().replace(/\/$/, "") ||
  "https://www.smpl-ai.com"
);

export const SITE_NAME = "SMPL.ai";

/**
 * Default / share description (search + Open Graph).
 * Keep in sync with SEO tag comparison Rev 1.0 (+ "close").
 */
export const SITE_DESCRIPTION =
  "SaaS FP&A for finance teams: ARR, pipeline, cash, and financial statements in one governed model for close. Every number board-ready, traceable to source.";

/**
 * Default browser-tab / search title for the marketing homepage.
 * Separator: | (house style).
 */
export const SITE_TITLE =
  "SaaS FP&A Software & Board Reporting, Built to Be Trusted | SMPL.ai";

/** Absolute URL to square logo for Google Organization schema (min 112×112 PNG/JPG). */
export function siteLogoUrl(path = "/brand/icon-512.png"): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Default 1200×630 share image (og:image / twitter:image; Bing + LinkedIn previews).
 * Next.js replaces a parent's `openGraph` wholesale when a page sets its own,
 * so pages that override `openGraph` must pass this in `images` explicitly.
 */
export const DEFAULT_OG_IMAGE = {
  url: siteLogoUrl("/brand/og-image.png"),
  width: 1200,
  height: 630,
  alt: SITE_NAME,
};

/** Absolute URL for a site path (canonical / og:url). */
export function sitePageUrl(path = "/"): string {
  if (!path || path === "/") return SITE_URL;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
