import type { PortableTextBlock } from "@portabletext/types";

export type TocHeading = {
  id: string;
  text: string;
  level: 2 | 3;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Plain text from a Portable Text block (span children only). */
export function portableBlockPlainText(block: PortableTextBlock): string {
  const children = Array.isArray(block.children) ? block.children : [];
  return children
    .map((child) => {
      if (!isRecord(child)) return "";
      return typeof child.text === "string" ? child.text : "";
    })
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

/** Concatenated plain text across Portable Text blocks (for thin-content checks). */
export function portableBodyPlainText(
  body?: PortableTextBlock[] | null,
): string {
  if (!body?.length) return "";
  return body
    .filter((block) => block._type === "block")
    .map((block) => portableBlockPlainText(block))
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

export function slugifyHeading(text: string): string {
  const slug = text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/['']/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "section";
}

function uniqueHeadingId(base: string, used: Map<string, number>): string {
  const count = used.get(base) ?? 0;
  used.set(base, count + 1);
  return count === 0 ? base : `${base}-${count + 1}`;
}

function blockStyle(block: PortableTextBlock): string | undefined {
  return typeof block.style === "string" ? block.style : undefined;
}

/**
 * Extract h2/h3 headings from a Portable Text body with stable, disambiguated ids.
 * Order matches document order so rendering can reuse the same id sequence.
 */
export function extractPortableHeadings(
  body?: PortableTextBlock[] | null,
): TocHeading[] {
  if (!body?.length) return [];

  const used = new Map<string, number>();
  const headings: TocHeading[] = [];

  for (const block of body) {
    if (block._type !== "block") continue;
    const style = blockStyle(block);
    if (style !== "h2" && style !== "h3") continue;

    const text = portableBlockPlainText(block);
    if (!text) continue;

    const id = uniqueHeadingId(slugifyHeading(text), used);
    headings.push({
      id,
      text,
      level: style === "h2" ? 2 : 3,
    });
  }

  return headings;
}

/** Map Portable Text block `_key` → heading id for anchored rendering. */
export function portableHeadingIdByKey(
  body?: PortableTextBlock[] | null,
): Map<string, string> {
  const map = new Map<string, string>();
  if (!body?.length) return map;

  const used = new Map<string, number>();

  for (const block of body) {
    if (block._type !== "block") continue;
    const style = blockStyle(block);
    if (style !== "h2" && style !== "h3") continue;

    const text = portableBlockPlainText(block);
    if (!text) continue;

    const key = typeof block._key === "string" ? block._key : undefined;
    if (!key) continue;

    map.set(key, uniqueHeadingId(slugifyHeading(text), used));
  }

  return map;
}
