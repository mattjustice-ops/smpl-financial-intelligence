import type { SalesAudience, SalesKbEntry, SalesTalkMatch, SalesTone } from "./types";

const STOP = new Set([
  "a",
  "an",
  "the",
  "is",
  "are",
  "was",
  "were",
  "do",
  "does",
  "did",
  "you",
  "your",
  "we",
  "our",
  "to",
  "of",
  "in",
  "on",
  "for",
  "and",
  "or",
  "with",
  "how",
  "what",
  "why",
  "when",
  "who",
  "can",
  "this",
  "that",
  "it",
  "be",
]);

/** Expand common sales/IT phrasings so KB keywords hit more reliably. */
const SYNONYM_EXPAND: Record<string, string[]> = {
  soc2: ["soc", "2", "compliance"],
  soc: ["soc2", "compliance"],
  encrypted: ["encryption", "tls"],
  encryption: ["encrypted", "tls"],
  tls: ["https", "encryption"],
  https: ["tls", "encryption"],
  sso: ["saml", "oidc", "single"],
  writeback: ["write-back", "erp"],
  subprocessors: ["vendors", "hosting"],
  subprocessor: ["vendors", "hosting"],
  residency: ["stored", "where"],
  hosted: ["hosting", "saas"],
  hosting: ["hosted", "saas"],
  customize: ["custom", "tailored", "configuration"],
  custom: ["customize", "tailored"],
  features: ["capabilities", "modules", "included"],
  mda: ["mda", "board", "commentary"],
  "md&a": ["mda", "board"],
  connector: ["connectors", "integration", "sync"],
  connectors: ["connector", "integration", "sync"],
  arr: ["mrr", "waterfall"],
  mrr: ["arr", "waterfall"],
};

export function tokenize(text: string): string[] {
  const base = text
    .toLowerCase()
    .replace(/soc\s*2/g, " soc2 ")
    .replace(/write[\s-]?back/g, " writeback ")
    .replace(/[^a-z0-9$%\-\s]/g, " ")
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length > 1 && !STOP.has(t));

  const out: string[] = [];
  const seen = new Set<string>();
  for (const token of base) {
    if (!seen.has(token)) {
      seen.add(token);
      out.push(token);
    }
    for (const extra of SYNONYM_EXPAND[token] ?? []) {
      if (!seen.has(extra) && !STOP.has(extra)) {
        seen.add(extra);
        out.push(extra);
      }
    }
  }
  return out;
}

function fieldScore(queryTokens: string[], field: string, weight: number): number {
  if (!field) return 0;
  const hay = field.toLowerCase();
  let score = 0;
  for (const token of queryTokens) {
    if (hay.includes(token)) {
      score += weight;
      // Extra boost for whole-word-ish hits
      if (new RegExp(`(?:^|\\b)${escapeRegExp(token)}(?:\\b|$)`).test(hay)) {
        score += weight * 0.35;
      }
    }
  }
  // Phrase boost: multi-word query substring
  const phrase = queryTokens.join(" ");
  if (phrase.length >= 6 && hay.includes(phrase)) {
    score += weight * 2.5;
  }
  return score;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function audienceAllows(entry: SalesKbEntry, audience: SalesAudience | null): boolean {
  if (!audience || audience === "general") return true;
  const audiences = entry.audiences ?? ["general"];
  return audiences.includes(audience) || audiences.includes("general");
}

function toneAllows(entry: SalesKbEntry, includeInternalDeep: boolean): boolean {
  const tone: SalesTone = entry.tone ?? "external_safe";
  if (tone === "internal_deep" && !includeInternalDeep) return false;
  return true;
}

export function scoreEntry(question: string, entry: SalesKbEntry): number {
  const tokens = tokenize(question);
  if (tokens.length === 0) return 0;

  let score = 0;
  score += fieldScore(tokens, entry.title, 3.2);
  score += fieldScore(tokens, (entry.topics ?? []).join(" "), 2.8);
  score += fieldScore(tokens, (entry.keywords ?? []).join(" "), 2.4);
  score += fieldScore(tokens, entry.answer, 0.45);
  score += fieldScore(tokens, entry.id.replace(/-/g, " "), 1.2);

  // Prefer external_safe slightly when both would match
  if ((entry.tone ?? "external_safe") === "external_safe") {
    score += 0.15;
  }

  // Normalize lightly by query length so short queries aren't drowned
  return score / Math.sqrt(Math.max(tokens.length, 1));
}

export type RetrieveOptions = {
  audience?: SalesAudience | null;
  includeInternalDeep?: boolean;
  limit?: number;
  minScore?: number;
};

export function retrieveSalesAnswers(
  question: string,
  entries: SalesKbEntry[],
  options: RetrieveOptions = {},
): SalesTalkMatch[] {
  const audience = options.audience ?? null;
  const includeInternalDeep = options.includeInternalDeep ?? false;
  const limit = options.limit ?? 3;
  const minScore = options.minScore ?? 1.35;

  const scored: SalesTalkMatch[] = [];
  for (const entry of entries) {
    if (!audienceAllows(entry, audience)) continue;
    if (!toneAllows(entry, includeInternalDeep)) continue;
    const score = scoreEntry(question, entry);
    if (score >= minScore) {
      scored.push({ entry, score });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit);
}

/** Detect question-like utterances for live STT. */
export function looksLikeQuestion(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 8) return false;
  if (/\?\s*$/.test(trimmed)) return true;

  const lower = trimmed.toLowerCase();
  const starters = [
    "how ",
    "what ",
    "why ",
    "when ",
    "who ",
    "where ",
    "which ",
    "can you",
    "could you",
    "would you",
    "do you",
    "does ",
    "is there",
    "are you",
    "what's",
    "whats ",
    "how's",
    "hows ",
    "how do",
    "how does",
    "how much",
    "how many",
    "tell me",
  ];
  if (starters.some((s) => lower.startsWith(s))) return true;

  const objections = [
    "cube already",
    "isn't this just",
    "isn't this a",
    "won't the incumbents",
    "quickbooks will",
    "rillet already",
    "i'm not sure",
    "im not sure",
    "not sure the",
  ];
  return objections.some((o) => lower.includes(o));
}

export function normalizeUtterance(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
