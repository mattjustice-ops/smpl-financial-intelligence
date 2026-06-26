/** Canonical marketing site URL (use www — apex may still point at Squarespace). */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL?.trim().replace(/\/$/, "") ||
  "https://www.smpl-ai.com"
);

export const SITE_NAME = "SMPL.ai";

export const SITE_DESCRIPTION =
  "AI operating system for SaaS finance teams — pipeline, ARR, cash, and board-ready reporting in one model.";

/** Absolute URL to square logo for Google Organization schema (min 112×112 PNG/JPG). */
export function siteLogoUrl(path = "/brand/smpl-logo.png"): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
