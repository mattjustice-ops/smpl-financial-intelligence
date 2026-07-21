import "server-only";

import type { SalesAudience, SalesKbEntry } from "./types";

const MODEL = process.env.ANTHROPIC_MODEL?.trim() || "claude-haiku-4-5-20251001";

function audienceLabel(audience: SalesAudience | null): string {
  switch (audience) {
    case "cfo":
      return "CFO / finance leader";
    case "it":
      return "IT / security buyer";
    case "fpa":
      return "FP&A practitioner";
    case "ceo":
      return "CEO / operator";
    case "engineer":
      return "engineer / architect";
    case "investor":
      return "investor";
    default:
      return "general business audience";
  }
}

/**
 * Rephrase a matched KB answer for the audience. Fail closed: returns null on any issue.
 * MUST NOT add facts, numbers, or claims absent from the KB text.
 */
export async function rephraseKbAnswer(params: {
  question: string;
  entry: SalesKbEntry;
  audience: SalesAudience | null;
}): Promise<string | null> {
  const apiKey = process.env.ANTHROPIC_API_KEY?.trim();
  if (!apiKey) return null;

  const system = [
    "You rephrase vetted sales talk-track answers for live meetings.",
    "Rules (non-negotiable):",
    "1. Use ONLY the provided KB answer text. Do not add facts, numbers, names, dates, or claims.",
    "2. Do not invent ROI, pricing, TAM, customer counts, or funding details.",
    "3. Keep 2–4 short sentences, sayable out loud. No preamble like 'Great question.'",
    "4. If the KB answer is a DEFLECT instruction, keep the deflection intent; do not invent a number.",
    "5. If you cannot rephrase without adding information, return the KB answer unchanged.",
    "Return plain text only — no JSON, no markdown.",
  ].join("\n");

  const user = [
    `Audience: ${audienceLabel(params.audience)}`,
    `Prospect question: ${params.question}`,
    `KB entry id: ${params.entry.id}`,
    `Confidence: ${params.entry.confidence}`,
    "KB answer (source of truth):",
    params.entry.answer,
  ].join("\n\n");

  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 320,
        temperature: 0,
        system,
        messages: [{ role: "user", content: user }],
      }),
    });

    if (!res.ok) return null;
    const data = (await res.json()) as {
      content?: Array<{ type?: string; text?: string }>;
    };
    const text = data.content
      ?.filter((block) => block.type === "text" && typeof block.text === "string")
      .map((block) => block.text!.trim())
      .join("\n")
      .trim();

    if (!text || text.length < 8) return null;
    // Reject obvious model refusals / freelancing markers
    if (/NO_PREPARED_ANSWER/i.test(text)) return null;
    return text;
  } catch {
    return null;
  }
}
