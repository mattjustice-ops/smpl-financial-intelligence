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
  "FP&A for SaaS finance teams. Unify ARR, pipeline, cash, and financial statements into one governed model for close. Every number board-ready and traceable to its source.";

/**
 * Default browser-tab / search title for the marketing homepage.
 * Separator: | (house style).
 */
export const SITE_TITLE =
  "SaaS FP&A Software & Board Reporting, Built to Be Trusted | SMPL.ai";

/** Absolute URL to square logo for Google Organization schema (min 112×112 PNG/JPG). */
export function siteLogoUrl(path = "/brand/smpl-logo.png"): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Absolute URL for a site path (canonical / og:url). */
export function sitePageUrl(path = "/"): string {
  if (!path || path === "/") return SITE_URL;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
