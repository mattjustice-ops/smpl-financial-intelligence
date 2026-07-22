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
  // Generic glue that otherwise substring-matches almost every English sentence
  "as",
  "at",
  "by",
  "from",
  "into",
  "about",
  "than",
  "then",
  "also",
  "just",
  "any",
  "all",
  "not",
  "no",
  "if",
  "so",
  "up",
  "out",
  "off",
  "per",
  "via",
  "me",
  "my",
  "their",
  "them",
  "they",
  "have",
  "has",
  "had",
  "will",
  "would",
  "could",
  "should",
  "been",
  "being",
  "am",
  "same",
  "very",
  "more",
  "most",
  "some",
  "such",
  "over",
  "under",
  "between",
  "there",
  "here",
  "which",
  "where",
]);

/** Expand common sales/IT phrasings so KB keywords hit more reliably. */
const SYNONYM_EXPAND: Record<string, string[]> = {
  soc2: ["soc", "compliance"],
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
  moat: ["defensibility", "architecture"],
  differentiator: ["differentiation"],
  differentiation: ["differentiator"],
  defensibility: ["moat"],
  chatgpt: ["llm"],
  powerbi: ["bi"],
};

/**
 * High-signal phrases: if the query contains one, entries that also carry it
 * in title/topics/keywords get a large boost; others get a mild penalty so
 * weak bag-of-words matches cannot win.
 */
const KEY_PHRASE_GROUPS: string[][] = [
  [
    "moat",
    "competitive moat",
    "competitive advantage",
    "hard to copy",
    "difficult to copy",
    "defensibility",
    "architecture as a moat",
    "architecture-as-moat",
    "what is your moat",
    "is ai your advantage",
  ],
  [
    "differentiator",
    "differentiation",
    "what makes you different",
    "what makes smpl different",
    "how are you different",
  ],
  [
    "ai security",
    "llm security",
    "how do you handle ai security",
    "what are you doing for ai security",
    "ai data security",
    "prompt security",
  ],
  [
    "train on our data",
    "train ai on our data",
    "do you train on our data",
    "do you train ai on our data",
    "training data",
    "train foundation models",
    "is our data used for training",
  ],
  [
    "hallucinat",
    "hallucinate",
    "hallucination",
    "hallucinations",
    "can ai hallucinate",
    "prevent hallucinations",
    "how do you prevent hallucinations",
    "does ai make things up",
  ],
  [
    "system architecture",
    "architecture overview",
    "how is it built",
    "tech stack",
    "tell me about your system architecture",
    "what is your architecture",
    "application architecture",
    "platform architecture",
  ],
  [
    "mosaic",
    "mosaic.fm",
    "mosiac",
    "mozaic",
    "why not mosaic",
    "vs mosaic",
    "why you vs mosaic",
    "bob finance",
  ],
  [
    "data security",
    "is our data secure",
    "is data secure",
    "how is our data secured",
    "secure our data",
  ],
  ["power bi", "powerbi", "why not power bi", "why you vs power bi", "vs power bi"],
  ["chatgpt", "chat gpt", "why not chatgpt", "why not just use chatgpt", "just use chatgpt"],
  ["tableau", "why not tableau", "why you vs tableau", "vs tableau"],
  ["snowflake", "why not snowflake", "why you vs snowflake", "vs snowflake"],
  ["why not excel", "why not just use excel", "just use excel", "replace excel"],
  ["seo tags", "meta tags", "open graph", "search console", "site seo", "marketing seo"],
  ["soc2", "soc 2", "soc-2"],
  ["implementation timeline", "how long is implementation", "four to six weeks", "4-6 weeks"],
  ["writeback", "write-back", "write back"],
  ["subprocessors", "sub-processors", "sub processors"],
];

export function tokenize(text: string): string[] {
  const base = text
    .toLowerCase()
    .replace(/soc\s*2/g, " soc2 ")
    .replace(/write[\s-]?back/g, " writeback ")
    .replace(/power\s*bi/g, " powerbi ")
    .replace(/chat\s*gpt/g, " chatgpt ")
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
      if (!seen.has(extra) && !STOP.has(extra) && extra.length > 1) {
        seen.add(extra);
        out.push(extra);
      }
    }
  }
  return out;
}

function wholeWordMatch(hay: string, token: string): boolean {
  return new RegExp(`(?:^|\\b)${escapeRegExp(token)}(?:\\b|$)`).test(hay);
}

function fieldScore(queryTokens: string[], field: string, weight: number): number {
  if (!field) return 0;
  const hay = field.toLowerCase();
  let score = 0;
  for (const token of queryTokens) {
    const whole = wholeWordMatch(hay, token);
    // Short tokens (len <= 3) are substring-pollution magnets ("as" in "database").
    // Only count whole-word hits, and at reduced weight.
    if (token.length <= 3) {
      if (whole) score += weight * 0.35;
      continue;
    }
    if (!hay.includes(token)) continue;
    // Substring hit without a word boundary is weak — discount heavily
    if (!whole) {
      score += weight * 0.15;
      continue;
    }
    score += weight;
    score += weight * 0.35;
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

function structuredText(entry: SalesKbEntry): string {
  return [
    entry.title,
    ...(entry.topics ?? []),
    ...(entry.keywords ?? []),
    entry.id.replace(/-/g, " "),
  ]
    .join(" ")
    .toLowerCase();
}

function keyPhraseBoost(question: string, entry: SalesKbEntry): number {
  const q = question
    .toLowerCase()
    .replace(/soc\s*2/g, "soc2")
    .replace(/write[\s-]?back/g, "writeback")
    .replace(/power\s*bi/g, "power bi")
    .replace(/chat\s*gpt/g, "chatgpt");
  const structured = structuredText(entry)
    .replace(/power\s*bi/g, "power bi")
    .replace(/chat\s*gpt/g, "chatgpt");
  let boost = 0;

  for (const phrases of KEY_PHRASE_GROUPS) {
    const qHit = phrases.some((p) => q.includes(p));
    if (!qHit) continue;
    const eHit = phrases.some((p) => structured.includes(p));
    if (eHit) {
      boost += 14;
    } else {
      // Query asked something specific; this entry does not carry that signal
      boost -= 3;
    }
  }
  return boost;
}

/** Exact keyword / topic phrase hits (beyond bag-of-words tokens). */
function phraseFieldBoost(question: string, entry: SalesKbEntry): number {
  const q = question.toLowerCase();
  let boost = 0;
  const phrases = [...(entry.keywords ?? []), ...(entry.topics ?? [])];
  for (const phrase of phrases) {
    const p = phrase.toLowerCase().trim();
    if (p.length < 4) continue;
    if (q.includes(p)) {
      boost += p.split(/\s+/).length >= 2 ? 6 : 3.5;
    }
  }
  return boost;
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

  let structured =
    fieldScore(tokens, entry.title, 3.2) +
    fieldScore(tokens, (entry.topics ?? []).join(" "), 2.8) +
    fieldScore(tokens, (entry.keywords ?? []).join(" "), 2.4) +
    fieldScore(tokens, entry.id.replace(/-/g, " "), 1.2);

  // Answer body is supporting evidence only — never enough alone to win
  const answerScore = fieldScore(tokens, entry.answer, 0.2);
  const keyBoost = keyPhraseBoost(question, entry);

  let score = structured + answerScore + keyBoost + phraseFieldBoost(question, entry);

  // Prefer external_safe slightly when both would match
  if ((entry.tone ?? "external_safe") === "external_safe") {
    score += 0.15;
  }

  // If nothing hit title/topics/keywords/id, collapse weak answer-only matches
  if (structured < 0.5 && keyBoost <= 0) {
    score *= 0.25;
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
  // Raised slightly so weak bag-of-words noise deflects instead of wrong-carding
  const minScore = options.minScore ?? 2.1;

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
