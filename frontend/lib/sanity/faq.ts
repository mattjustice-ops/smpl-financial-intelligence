import type { PortableTextBlock } from "@portabletext/types";

import { portableBlockPlainText } from "@/lib/sanity/headings";

export type FaqItem = {
  question: string;
  answer: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function blockStyle(block: PortableTextBlock): string | undefined {
  return typeof block.style === "string" ? block.style : undefined;
}

function isListItem(block: PortableTextBlock): boolean {
  return typeof (block as { listItem?: unknown }).listItem === "string";
}

/**
 * Extract FAQ Q&A pairs after an h2 whose text is "FAQ".
 * Expects alternating normal paragraphs: question then answer
 * (questions often start as bold markdown rendered as strong spans).
 */
export function extractFaqFromBody(
  body?: PortableTextBlock[] | null,
): FaqItem[] {
  if (!body?.length) return [];

  let inFaq = false;
  const items: FaqItem[] = [];
  let pendingQuestion: string | null = null;

  for (const block of body) {
    if (!isRecord(block) || block._type !== "block") continue;
    const style = blockStyle(block as PortableTextBlock);

    if (style === "h2" || style === "h3") {
      const heading = portableBlockPlainText(block as PortableTextBlock);
      if (style === "h2" && /^faq$/i.test(heading)) {
        inFaq = true;
        pendingQuestion = null;
        continue;
      }
      if (inFaq) break;
      continue;
    }

    if (!inFaq || style !== "normal" || isListItem(block as PortableTextBlock)) {
      continue;
    }

    const text = portableBlockPlainText(block as PortableTextBlock);
    if (!text) continue;

    if (!pendingQuestion) {
      pendingQuestion = text.replace(/\?*$/, "").trim() + (text.includes("?") ? "?" : "");
      if (!pendingQuestion.endsWith("?")) {
        pendingQuestion = `${pendingQuestion}?`;
      }
      continue;
    }

    items.push({ question: pendingQuestion, answer: text });
    pendingQuestion = null;
  }

  return items.filter((item) => item.question.length > 3 && item.answer.length > 3);
}
