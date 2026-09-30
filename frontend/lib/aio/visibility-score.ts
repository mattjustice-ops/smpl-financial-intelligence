/**
 * Visibility scoring that keeps three outcomes separate:
 *   - prose mention: SMPL named in the answer's own text (citation-pill labels excluded)
 *   - vendor recommendation: SMPL presented as a product to consider
 *   - source citation: a SMPL-owned page supports the answer
 * and never reports "no citation" when the citation evidence was not captured.
 */

export const VISIBILITY_SCORER_VERSION = "visibility_v1";

export type CitationStatus =
  /** Every displayed source captured with a URL (including sources hidden behind "+N"). */
  | "complete"
  /** URLs captured for visible pills, but some hidden "+N" sources were not expanded. */
  | "partial"
  /** No URLs captured; only citation-pill labels survive in the saved answer text. */
  | "labels_only"
  /** Structured capture confirmed the answer displayed no citations. */
  | "none_shown"
  /** No citation evidence was collected at all. */
  | "not_collected";

export type CitedSource = {
  url: string;
  title?: string | null;
  publisher?: string | null;
  paragraph?: string | null;
  hidden?: boolean;
};

export type RecommendationLevel =
  | "none"
  | "listed"
  | "shortlisted"
  | "recommended"
  | "top_pick";

export type SmplCitation =
  | "yes"
  | "no"
  /** No SMPL among the sources we could see, but some sources were never captured. */
  | "not_in_visible_sources"
  | "unknown";

export type CitationVisibility =
  | "none"
  /** An SMPL pill or source was on screen without expanding "+N". */
  | "visible"
  /** SMPL appeared only among the sources hidden behind a "+N" pill. */
  | "hidden_only"
  /** Older capture: hidden sources were never collected, so visibility cannot be told apart. */
  | "unknown";

export type VisibilityInput = {
  answerText: string;
  /** Answer text with citation pills removed structurally (capture v2). */
  proseText?: string | null;
  sources?: CitedSource[];
  /** Citation-pill labels read structurally (capture v2). */
  citationLabels?: string[];
  citationStatus: CitationStatus;
};

export type VisibilityScore = {
  scorerVersion: string;
  proseSource: "structural" | "heuristic_label_strip";
  proseMention: boolean;
  proseVariants: string[];
  proseSnippets: string[];
  recommendation: RecommendationLevel;
  vendorRecommended: boolean;
  recommendationEvidence: string | null;
  citationStatus: CitationStatus;
  smplCitation: SmplCitation;
  smplCitationVisibility: CitationVisibility;
  smplCitationUrlVerified: boolean;
  smplSources: CitedSource[];
  smplCitationLabels: string[];
  sourceCount: number;
  hiddenSourceMarkers: number;
};

const LEVEL_RANK: Record<RecommendationLevel, number> = {
  none: 0,
  listed: 1,
  shortlisted: 2,
  recommended: 3,
  top_pick: 4,
};

function maxLevel(a: RecommendationLevel, b: RecommendationLevel): RecommendationLevel {
  return LEVEL_RANK[a] >= LEVEL_RANK[b] ? a : b;
}

const STRONG_BRAND = /\bSMPL(?:\.ai|[ -]AI)\b|\b(?:www\.)?smpl-ai\.com\b/gi;
/** Bare "SMPL" (uppercase) only counts when a strong variant is also present, since
 * "SMPL" alone is a common unrelated acronym (e.g. the SMPL body model). */
const BARE_BRAND = /\bSMPL\b(?![-.\s]?(?:X|H|body|model|parameters?)\b)/g;

const PEER_NAMES = [
  "Drivetrain", "Cube", "Pigment", "Runway", "Mosaic", "Anaplan", "Abacum", "Aleph", "Planful", "Vena",
  "Datarails", "Centage", "Workday", "Jirav", "Fathom", "Prophix", "Causal", "Finmark", "OneStream",
];
const PEERS = new RegExp(`\\b(${PEER_NAMES.join("|")})\\b`, "gi");

export function isSmplUrl(raw: string): boolean {
  try {
    const host = new URL(raw).hostname.toLowerCase();
    return host === "smpl-ai.com" || host.endsWith(".smpl-ai.com");
  } catch {
    return false;
  }
}

/** Drops tracking params and fragments so the same page counts once. */
export function normalizeSourceUrl(raw: string): string | null {
  try {
    const u = new URL(raw.trim());
    if (!/^https?:$/.test(u.protocol)) return null;
    u.hash = "";
    for (const k of [...u.searchParams.keys()]) {
      if (/^utm_/i.test(k)) u.searchParams.delete(k);
    }
    u.hostname = u.hostname.toLowerCase();
    let s = u.toString();
    if (u.pathname !== "/" && s.endsWith("/") && !u.search) s = s.slice(0, -1);
    return s;
  } catch {
    return null;
  }
}

export function sourceDomain(raw: string): string | null {
  try {
    return new URL(raw).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** Link hosts that belong to the answer UI, not to cited sources. */
export function isInterfaceUrl(raw: string): boolean {
  const d = sourceDomain(raw);
  return !d || /(^|\.)(chatgpt\.com|openai\.com|oaistatic\.com)$/.test(d);
}

const HIDDEN_MARKER = /^\+\d+$/;

/**
 * Removes citation-pill label lines from legacy innerText captures.
 * A pill renders as its own short line directly after a paragraph line that ends in
 * whitespace, optionally followed by a "+N" line for extra hidden sources.
 */
export function stripCitationLabelsHeuristic(text: string): {
  prose: string;
  labels: string[];
  hiddenMarkers: number;
} {
  const lines = text.split("\n");
  const keep: string[] = [];
  const labels: string[] = [];
  let hiddenMarkers = 0;
  let prevWasPill = false;
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (HIDDEN_MARKER.test(t)) {
      hiddenMarkers += Number(t.slice(1));
      prevWasPill = true;
      continue;
    }
    const prev = i > 0 ? lines[i - 1] : "";
    const labelShape =
      t.length > 0 && t.length <= 60 && !lines[i].includes("\t") && !/[.:!?]$/.test(t);
    // Consecutive pills render as back-to-back label lines ("Pigment\n+2\nPigment\n+2").
    const afterParagraph = prev.trim().length > 0 && /\s$/.test(prev);
    if (labelShape && (afterParagraph || prevWasPill)) {
      labels.push(t);
      prevWasPill = true;
      continue;
    }
    prevWasPill = false;
    keep.push(lines[i]);
  }
  return { prose: keep.join("\n"), labels, hiddenMarkers };
}

type BrandHit = { match: string; index: number };

export function findBrandMentions(text: string): BrandHit[] {
  const hits: BrandHit[] = [];
  for (const m of text.matchAll(STRONG_BRAND)) hits.push({ match: m[0], index: m.index ?? 0 });
  if (hits.length) {
    const taken = new Set(hits.map((h) => h.index));
    for (const m of text.matchAll(BARE_BRAND)) {
      const idx = m.index ?? 0;
      if (!taken.has(idx)) hits.push({ match: m[0], index: idx });
    }
  }
  return hits.sort((a, b) => a.index - b.index);
}

export function isBrandLabel(label: string): boolean {
  const t = label.trim();
  return new RegExp(`^(?:${STRONG_BRAND.source})$`, "i").test(t) || /^SMPL$/.test(t);
}

function lineAround(text: string, index: number): string {
  const start = text.lastIndexOf("\n", index - 1) + 1;
  const end = text.indexOf("\n", index);
  return text.slice(start, end < 0 ? undefined : end);
}

function sentenceAround(text: string, index: number): string {
  const before = text.slice(0, index);
  const start = Math.max(
    0,
    ...[".", "!", "?", "\n"].map((c) => before.lastIndexOf(c) + 1),
  );
  const rel = text.slice(index).search(/[.!?\n](?:\s|$)/);
  const end = rel < 0 ? text.length : index + rel + 1;
  return text.slice(start, end).replace(/\s+/g, " ").trim();
}

function peerCount(s: string): number {
  return (s.match(PEERS) || []).length;
}

/** Case-sensitive so FP&A vocabulary ("cash runway", "data cube") is not read as a vendor. */
const PEERS_EXACT = new RegExp(`\\b(${PEER_NAMES.join("|")})\\b`, "g");

/** Distinct peer FP&A vendors named in text. */
export function vendorsMentioned(text: string): string[] {
  return [...new Set([...text.matchAll(PEERS_EXACT)].map((m) => m[0]))].sort();
}

const BRAND_ALT = "SMPL(?:\\.ai|[ -]AI)?|(?:www\\.)?smpl-ai\\.com";
/** SMPL as the author of advice ("according to SMPL.ai", "SMPL.ai's guide recommends"). */
const ATTRIBUTION = new RegExp(
  `(?:according\\s+to|per|as\\s+(?:noted|described|explained)\\s+(?:by|in)|source[sd]?:?)\\s+(?:the\\s+)?(?:${BRAND_ALT})|(?:${BRAND_ALT})(?:'s)?\\s+(?:\\w+\\s+){0,2}?(?:recommends?|suggests?|argues?|notes?|says?|explains?|describes?|writes?|frames?|defines?|points\\s+out|guide|blog|article|post|glossary|page|checklist)\\b`,
  "i",
);

function levelForHit(text: string, hit: BrandHit): { level: RecommendationLevel; evidence: string } {
  const line = lineAround(text, hit.index);
  const sentence = sentenceAround(text, hit.index);
  const trimmedLine = line.trim();
  const brandStartsLine = new RegExp(`^(?:[-•*]|\\d+[.)])?\\s*\\**\\s*(?:${BRAND_ALT})\\b`, "i").test(trimmedLine);
  const tableRow = line.includes("\t") || /^\s*\|/.test(line);
  const listItem = brandStartsLine && !tableRow;
  const attribution = ATTRIBUTION.test(sentence);
  const peers = peerCount(sentence);

  let level: RecommendationLevel = "none";

  if (tableRow && brandStartsLine) level = maxLevel(level, "listed");
  if (listItem && !attribution) level = maxLevel(level, "listed");

  const productCue =
    /\b(option|alternative|platform|tool|vendor|product|solution|consider|worth\s+(?:a\s+)?(?:look|looking\s+at|evaluating|considering)|newer|emerging|also\s+look)\b/i;
  if (!attribution && productCue.test(sentence)) level = maxLevel(level, "listed");
  if (!attribution && peers > 0 && /,|\band\b|\bor\b/.test(sentence)) level = maxLevel(level, "listed");

  const ranked = /^\s*(\d+)[.)]\s/.exec(trimmedLine);
  if (ranked && brandStartsLine && Number(ranked[1]) <= 5) level = maxLevel(level, "shortlisted");
  if (
    new RegExp(
      `(?:start(?:ing)?\\s+(?:the\\s+|your\\s+)?evaluation\\s+with|focus(?:ing)?\\s+(?:the\\s+|your\\s+)?evaluation\\s+on|shortlist(?:ed)?|narrow(?:ed)?\\s+(?:it\\s+)?(?:down\\s+)?to)[^.!?\\n]{0,220}(?:${BRAND_ALT})`,
      "i",
    ).test(sentence)
  ) {
    level = maxLevel(level, "shortlisted");
  }

  if (!attribution && !tableRow) {
    if (
      /\b(recommend(?:ed)?\s+(?:SMPL|it)|worth\s+evaluating|strong\s+(?:option|candidate|fit)|(?:good|direct|close|strong)\s+(?:fit|match)|well[- ]suited)\b/i.test(
        sentence,
      )
    ) {
      level = maxLevel(level, peers <= 1 ? "recommended" : "shortlisted");
    }
    const after = text.slice(hit.index, hit.index + 450);
    const inv = after.search(/\bi(?:'d|\s+would)\s+investigate\s+it\b/i);
    if (inv >= 0 && peerCount(after.slice(0, inv)) === 0) level = maxLevel(level, "recommended");
    if (
      peers === 0 &&
      /\b(top\s*pick|best\s+(?:choice|option)|my\s+(?:top\s+)?recommendation|i(?:'d|\s+would)\s+(?:pick|choose|go\s+with))\b/i.test(
        sentence,
      )
    ) {
      level = maxLevel(level, "top_pick");
    }
  }

  return { level, evidence: tableRow ? trimmedLine.slice(0, 200) : sentence.slice(0, 300) };
}

export function scoreVisibility(input: VisibilityInput): VisibilityScore {
  const structural = typeof input.proseText === "string";
  const stripped = structural
    ? { prose: input.proseText as string, labels: input.citationLabels ?? [], hiddenMarkers: 0 }
    : stripCitationLabelsHeuristic(input.answerText || "");
  const prose = stripped.prose;

  const hits = findBrandMentions(prose);
  let recommendation: RecommendationLevel = "none";
  let recommendationEvidence: string | null = null;
  for (const h of hits) {
    const r = levelForHit(prose, h);
    if (LEVEL_RANK[r.level] > LEVEL_RANK[recommendation]) {
      recommendation = r.level;
      recommendationEvidence = r.evidence;
    }
  }

  const sources = (input.sources ?? []).filter((s) => s.url && !isInterfaceUrl(s.url));
  const smplSources = sources.filter((s) => isSmplUrl(s.url));
  const smplCitationLabels = stripped.labels.filter(isBrandLabel);
  const isSmplSource = (s: CitedSource) =>
    isSmplUrl(s.url) || isBrandLabel(s.publisher ?? "") || /\bSMPL\.ai\b/i.test(s.title ?? "");

  let smplCitation: SmplCitation;
  if (smplCitationLabels.length || sources.some(isSmplSource)) smplCitation = "yes";
  else if (input.citationStatus === "complete" || input.citationStatus === "none_shown") smplCitation = "no";
  else if (input.citationStatus === "not_collected") smplCitation = "unknown";
  else smplCitation = "not_in_visible_sources";

  let smplCitationVisibility: CitationVisibility = "none";
  if (smplCitation === "yes") {
    if (!structural) smplCitationVisibility = "unknown";
    else if (smplCitationLabels.length || sources.some((s) => !s.hidden && isSmplSource(s))) smplCitationVisibility = "visible";
    else smplCitationVisibility = "hidden_only";
  }

  return {
    scorerVersion: VISIBILITY_SCORER_VERSION,
    proseSource: structural ? "structural" : "heuristic_label_strip",
    proseMention: hits.length > 0,
    proseVariants: [...new Set(hits.map((h) => h.match))],
    proseSnippets: hits.slice(0, 3).map((h) => sentenceAround(prose, h.index).slice(0, 240)),
    recommendation,
    vendorRecommended: recommendation !== "none",
    recommendationEvidence,
    citationStatus: input.citationStatus,
    smplCitation,
    smplCitationVisibility,
    smplCitationUrlVerified: smplSources.length > 0,
    smplSources,
    smplCitationLabels,
    sourceCount: sources.length,
    hiddenSourceMarkers: stripped.hiddenMarkers,
  };
}

/**
 * Status for captures made before structured citation capture: URL lists came from
 * every link in the answer, so sources behind "+N" pills were never collected.
 */
export function legacyCitationStatus(answerText: string, urls: string[]): CitationStatus {
  const { labels, hiddenMarkers } = stripCitationLabelsHeuristic(answerText || "");
  const real = urls.filter((u) => !isInterfaceUrl(u));
  if (real.length === 0) return labels.length || hiddenMarkers ? "labels_only" : "not_collected";
  return hiddenMarkers > 0 ? "partial" : "complete";
}

export type DomainSummaryRow = { domain: string; answers: number; sources: number };

/** Domain counts derived from the same per-answer source lists the report prints. */
export function domainSummary(records: Array<{ sources: CitedSource[] }>): DomainSummaryRow[] {
  const map = new Map<string, DomainSummaryRow>();
  for (const r of records) {
    const seen = new Set<string>();
    const pages = new Set<string>();
    for (const s of r.sources) {
      if (isInterfaceUrl(s.url)) continue;
      const d = sourceDomain(s.url);
      const n = normalizeSourceUrl(s.url);
      if (!d || !n || pages.has(n)) continue;
      pages.add(n);
      const row = map.get(d) ?? { domain: d, answers: 0, sources: 0 };
      row.sources += 1;
      if (!seen.has(d)) {
        row.answers += 1;
        seen.add(d);
      }
      map.set(d, row);
    }
  }
  return [...map.values()].sort((a, b) => b.answers - a.answers || b.sources - a.sources);
}

export const COMPETITOR_DOMAINS: Record<string, string> = {
  "getaleph.com": "Aleph",
  "pigment.com": "Pigment",
  "kb.pigment.com": "Pigment",
  "cubesoftware.com": "Cube",
  "abacum.ai": "Abacum",
  "drivetrain.ai": "Drivetrain",
  "workday.com": "Workday Adaptive Planning",
  "doc.workday.com": "Workday Adaptive Planning",
  "venasolutions.com": "Vena",
  "datarails.com": "Datarails",
  "planful.com": "Planful",
  "anaplan.com": "Anaplan",
  "support.anaplan.com": "Anaplan",
  "mosaic.tech": "Mosaic",
  "runway.com": "Runway",
  "prophix.com": "Prophix",
  "jirav.com": "Jirav",
  "fathomhq.com": "Fathom",
  "support.fathomhq.com": "Fathom",
  "centage.com": "Centage",
  "causal.app": "Causal",
  "onestream.com": "OneStream",
};

export function competitorForUrl(raw: string): string | null {
  const d = sourceDomain(raw);
  if (!d) return null;
  if (COMPETITOR_DOMAINS[d]) return COMPETITOR_DOMAINS[d];
  const parent = Object.keys(COMPETITOR_DOMAINS).find((k) => d.endsWith(`.${k}`));
  return parent ? COMPETITOR_DOMAINS[parent] : null;
}
