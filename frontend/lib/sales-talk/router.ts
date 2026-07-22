import "server-only";

import type { SalesAudience, SalesKbEntry, SalesTalkMatch } from "./types";
import { DEFAULT_MIN_SCORE, keywordBestMatches, retrieveSalesAnswers } from "./retrieve";

const MODEL = process.env.ANTHROPIC_MODEL?.trim() || "claude-haiku-4-5-20251001";

export type RouterResult = {
  matches: SalesTalkMatch[];
  /** How the final shortlist was chosen. */
  source: "router" | "keyword" | "abstain";
};

type Candidate = { id: string; title: string; topics: string[]; score: number };

/**
 * Optional retrieve router: Claude may ONLY choose IDs from the keyword shortlist.
 * Never invents answers. Fail closed to keyword best match, or empty (deflect) if
 * scores are weak / router abstains with no strong keyword hit.
 */
export async function retrieveWithOptionalRouter(params: {
  question: string;
  entries: SalesKbEntry[];
  audience?: SalesAudience | null;
  includeInternalDeep?: boolean;
  limit?: number;
  minScore?: number;
}): Promise<RouterResult> {
  const limit = params.limit ?? 3;
  const minScore = params.minScore ?? DEFAULT_MIN_SCORE;
  const retrieveOpts = {
    audience: params.audience ?? null,
    includeInternalDeep: params.includeInternalDeep ?? false,
    limit,
    minScore,
  };

  const shortlist = retrieveSalesAnswers(params.question, params.entries, {
    ...retrieveOpts,
    shortlist: true,
    shortlistLimit: 8,
    minScore: 0,
  });

  const keywordMatches = keywordBestMatches(params.question, params.entries, retrieveOpts);

  const apiKey = process.env.ANTHROPIC_API_KEY?.trim();
  if (!apiKey || shortlist.length === 0) {
    return {
      matches: keywordMatches,
      source: keywordMatches.length > 0 ? "keyword" : "abstain",
    };
  }

  const candidates: Candidate[] = shortlist.map((m) => ({
    id: m.entry.id,
    title: m.entry.title,
    topics: (m.entry.topics ?? []).slice(0, 6),
    score: Number(m.score.toFixed(2)),
  }));

  const allowed = new Set(candidates.map((c) => c.id));

  const system = [
    "You are a retrieval router for a sales talk-track knowledge base.",
    "Your ONLY job: pick which entry IDs from the provided candidate list best answer the prospect question.",
    "Rules (non-negotiable):",
    "1. Choose ONLY from the candidate IDs listed. Never invent IDs or answers.",
    "2. Return 1 to 3 IDs ordered best-first, or ABSTAIN if none fit well.",
    "3. Prefer the focused card for the question intent over a vaguely related card.",
    '4. Output JSON only: {"ids":["id1","id2"]} or {"ids":[],"abstain":true}',
  ].join("\n");

  const user = [
    `Prospect question: ${params.question}`,
    "Candidates (id | title | topics | keyword_score):",
    ...candidates.map(
      (c) => `- ${c.id} | ${c.title} | ${c.topics.join("; ")} | ${c.score}`,
    ),
  ].join("\n");

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
        max_tokens: 200,
        temperature: 0,
        system,
        messages: [{ role: "user", content: user }],
      }),
    });

    if (!res.ok) {
      return {
        matches: keywordMatches,
        source: keywordMatches.length > 0 ? "keyword" : "abstain",
      };
    }

    const data = (await res.json()) as {
      content?: Array<{ type?: string; text?: string }>;
    };
    const text = data.content
      ?.filter((block) => block.type === "text" && typeof block.text === "string")
      .map((block) => block.text!.trim())
      .join("\n")
      .trim();

    if (!text) {
      return {
        matches: keywordMatches,
        source: keywordMatches.length > 0 ? "keyword" : "abstain",
      };
    }

    const parsed = parseRouterJson(text);
    if (!parsed || parsed.abstain || parsed.ids.length === 0) {
      return {
        matches: keywordMatches,
        source: "abstain",
      };
    }

    const byId = new Map(shortlist.map((m) => [m.entry.id, m]));
    const routed: SalesTalkMatch[] = [];
    for (const id of parsed.ids) {
      if (!allowed.has(id)) continue;
      const match = byId.get(id);
      if (match) routed.push(match);
      if (routed.length >= limit) break;
    }

    if (routed.length === 0) {
      return {
        matches: keywordMatches,
        source: keywordMatches.length > 0 ? "keyword" : "abstain",
      };
    }

    if (routed[0]!.score < minScore * 0.55 && keywordMatches.length === 0) {
      return { matches: [], source: "abstain" };
    }

    return { matches: routed, source: "router" };
  } catch {
    return {
      matches: keywordMatches,
      source: keywordMatches.length > 0 ? "keyword" : "abstain",
    };
  }
}

function parseRouterJson(text: string): { ids: string[]; abstain?: boolean } | null {
  const trimmed = text.trim();
  const fence = trimmed.match(/\{[\s\S]*\}/);
  const raw = fence ? fence[0] : trimmed;
  try {
    const obj = JSON.parse(raw) as { ids?: unknown; abstain?: unknown };
    const ids = Array.isArray(obj.ids)
      ? obj.ids.filter((id): id is string => typeof id === "string" && id.length > 0)
      : [];
    return { ids, abstain: obj.abstain === true };
  } catch {
    return null;
  }
}
