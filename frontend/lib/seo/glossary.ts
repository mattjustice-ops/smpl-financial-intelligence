import type { PortableTextBlock } from "@portabletext/types";

import { portableBodyPlainText } from "@/lib/sanity/headings";

/**
 * Minimum Portable Text body length before a glossary term is worth indexing.
 * One-sentence stubs (~200 chars) get crawled-not-indexed in GSC and dilute the site.
 * Expand the Sanity body past this threshold to re-enable indexing + sitemap inclusion.
 */
export const GLOSSARY_INDEXABLE_BODY_CHARS = 800;

export function isGlossaryTermIndexable(
  body?: PortableTextBlock[] | null,
): boolean {
  return portableBodyPlainText(body).length >= GLOSSARY_INDEXABLE_BODY_CHARS;
}
