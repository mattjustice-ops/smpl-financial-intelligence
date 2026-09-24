import brandTruth from "@/lib/aio/data/brand_truth.json";

export type RecommendationStrength =
  | "none"
  | "mentioned"
  | "shortlisted"
  | "recommended"
  | "top_pick";

export type CompetitorEval = {
  name: string;
  mentioned: boolean;
  recommendation_strength: RecommendationStrength;
  explicit_rank: number | null;
};

export type AioEvaluation = {
  smpl_mentioned: boolean;
  smpl_name_variants_found: string[];
  recommendation_strength: RecommendationStrength;
  explicit_rank: number | null;
  prominence_score: number;
  smpl_cited: boolean;
  smpl_owned_domain_cited: boolean;
  smpl_cited_urls: string[];
  competitors: CompetitorEval[];
  positioning_accuracy: number;
  positioning_summary: string;
  incorrect_or_unverified_claims: string[];
  answer_relevance: number;
  notes: string;
};

/** Current scorer for new imports. Historical rows keep their stored evaluator_version. */
export const EVALUATOR_VERSION = "rules_v2";

/** Frozen label for audits scored before the first-window / Best-fit fixes. */
export const LEGACY_EVALUATOR_VERSION = "rules_v1";

const STRENGTH_RANK: Record<RecommendationStrength, number> = {
  none: 0,
  mentioned: 1,
  shortlisted: 2,
  recommended: 3,
  top_pick: 4,
};

function maxStrength(
  a: RecommendationStrength,
  b: RecommendationStrength,
): RecommendationStrength {
  return STRENGTH_RANK[a] >= STRENGTH_RANK[b] ? a : b;
}

export const DEFAULT_COMPETITORS = [
  "Abacum",
  "Aleph",
  "Anaplan",
  "Cube",
  "Datarails",
  "Drivetrain",
  "Mosaic",
  "Pigment",
  "Planful",
  "Prophix",
  "Runway",
  "Vena",
  "Workday Adaptive Planning",
] as const;

const SMPL_PATTERNS = [
  /\bSMPL\.ai\b/gi,
  /\bSMPL\b/g,
  /\bsmpl-ai\.com\b/gi,
  /\bwww\.smpl-ai\.com\b/gi,
];

const GOOD_POSITIONING = [
  "saas",
  "fp&a",
  "fpa",
  "board",
  "arr",
  "forecast",
  "budget",
  "governance",
  "deterministic",
  "reconcil",
  "lean",
  "finance team",
  "financial intelligence",
  "planning",
];

const UNVERIFIED_CLAIM_PATTERNS: Array<{ re: RegExp; label: string }> = [
  { re: /\bSOC\s*2\b/i, label: "SOC 2 claim near SMPL" },
  { re: /\bSSO\b/i, label: "SSO claim near SMPL" },
  { re: /\breplaces?\s+(ERP|NetSuite|Salesforce|QuickBooks)/i, label: "SoR replacement claim" },
  { re: /\bnative\s+integration\b/i, label: "native integration claim" },
  { re: /\bguarantees?\b/i, label: "guarantee language" },
];

function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

function strengthWeight(s: RecommendationStrength): number {
  switch (s) {
    case "none":
      return 0;
    case "mentioned":
      return 0.2;
    case "shortlisted":
      return 0.5;
    case "recommended":
      return 0.75;
    case "top_pick":
      return 1;
  }
}

function windowAround(text: string, index: number, radius = 180): string {
  const start = Math.max(0, index - radius);
  const end = Math.min(text.length, index + radius);
  return text.slice(start, end);
}

function findSmplMatches(
  answer: string,
): Array<{ match: string; index: number }> {
  const found: Array<{ match: string; index: number }> = [];
  const seen = new Set<number>();
  for (const re of SMPL_PATTERNS) {
    const flags = re.flags.includes("g") ? re.flags : `${re.flags}g`;
    const global = new RegExp(re.source, flags);
    let m: RegExpExecArray | null;
    while ((m = global.exec(answer))) {
      if (seen.has(m.index)) continue;
      seen.add(m.index);
      found.push({ match: m[0], index: m.index });
    }
  }
  return found.sort((a, b) => a.index - b.index);
}

function sentenceAround(answer: string, index: number): string {
  const before = answer.slice(0, index);
  const after = answer.slice(index);
  const startCandidates = [before.lastIndexOf("."), before.lastIndexOf("!"), before.lastIndexOf("?"), before.lastIndexOf("\n")];
  const start = Math.max(0, ...startCandidates.map((i) => i + 1));
  let endRel = after.search(/[.!?\n]/);
  if (endRel < 0) endRel = after.length;
  return answer.slice(start, index + endRel + 1).replace(/\s+/g, " ").trim();
}

function lineAround(answer: string, index: number): string {
  const start = answer.lastIndexOf("\n", index) + 1;
  const end = answer.indexOf("\n", index);
  return answer.slice(start, end < 0 ? undefined : end);
}

/** True when "best"/"Best fit" is table-header bleed, not a preference about SMPL. */
function isTableHeaderBestBleed(answer: string, index: number): boolean {
  const before = answer.slice(Math.max(0, index - 220), index);
  if (/\bbest\s+fit\b/i.test(before) && /\t|\|/.test(before)) return true;
  const line = lineAround(answer, index);
  // SMPL row in a TSV/markdown table is not itself a top_pick claim.
  if (/\t/.test(line) || /^\s*\|/.test(line)) return true;
  return false;
}

function peersInText(text: string): number {
  return (
    text.match(
      /\b(Drivetrain|Cube|Pigment|Runway|Mosaic|Anaplan|Abacum|Aleph|Planful|Vena|Datarails|Centage|Workday)\b/gi,
    ) || []
  ).length;
}

/**
 * rules_v2: score every SMPL mention (and whole-answer shortlist lists).
 * Preference language must bind to SMPL; bare "best" in a table header does not.
 */
function classifySmplStrength(answer: string): {
  strength: RecommendationStrength;
  explicit_rank: number | null;
  variants: string[];
} {
  const matches = findSmplMatches(answer);
  if (!matches.length) {
    return { strength: "none", explicit_rank: null, variants: [] };
  }

  const variants = unique(matches.map((m) => m.match));
  let strength: RecommendationStrength = "mentioned";
  let explicit_rank: number | null = null;

  const ranked = answer.match(
    new RegExp(
      `(?:^|\\n)\\s*(\\d+)[.)]\\s*[^\\n]{0,80}(?:SMPL\\.ai|SMPL|smpl-ai\\.com)`,
      "i",
    ),
  );
  if (ranked) {
    const n = Number(ranked[1]);
    if (n >= 1 && n <= 20) explicit_rank = n;
  }

  // Whole-answer shortlist / evaluation-start lists that include SMPL.
  const listPatterns: RegExp[] = [
    /(?:start(?:ing)?\s+(?:the\s+)?evaluation\s+with|i(?:'d|\s+would)\s+probably\s+start(?:\s+the\s+evaluation)?\s+with|shortlist(?:ed)?|narrow(?:ed)?\s+to)\s+[^.!?\n]{0,220}\bSMPL(?:\.ai)?\b/gi,
    /(?:worth\s+looking\s+at|newer\s+option(?:\s+worth\s+looking\s+at)?)\s+is\s+SMPL(?:\.ai)?\b/gi,
    /(?:Drivetrain|Cube|Pigment|Runway|Mosaic|Anaplan|Abacum|Aleph)(?:,|\s+and|\s+or)[^.!?\n]{0,160}\bSMPL(?:\.ai)?\b/gi,
    /\bSMPL(?:\.ai)?\b(?:,|\s+and|\s+or)[^.!?\n]{0,160}(?:Drivetrain|Cube|Pigment|Runway|Mosaic|Anaplan)/gi,
  ];
  for (const re of listPatterns) {
    re.lastIndex = 0;
    if (re.test(answer)) {
      strength = maxStrength(strength, "shortlisted");
    }
  }

  // Anaphoric recommend: "I'd investigate it" after a recent SMPL mention.
  const inv = answer.search(/\bi(?:'d|\s+would)\s+investigate\s+it\b/i);
  if (inv >= 0) {
    const prior = answer.slice(Math.max(0, inv - 450), inv);
    if (
      /\bSMPL(?:\.ai)?\b/i.test(prior) &&
      !/\b(Cube|Pigment|Drivetrain|Runway|Mosaic|Anaplan)\b[^.!?\n]{0,60}\bi(?:'d|\s+would)\s+investigate\s+it\b/i.test(
        answer.slice(Math.max(0, inv - 120), inv + 40),
      )
    ) {
      strength = maxStrength(strength, "recommended");
    }
  }

  if (explicit_rank === 1) {
    strength = maxStrength(strength, "top_pick");
  } else if (explicit_rank !== null && explicit_rank <= 5) {
    strength = maxStrength(strength, "shortlisted");
  }

  for (const m of matches) {
    const sentence = sentenceAround(answer, m.index);
    const sLower = sentence.toLowerCase();
    const win = windowAround(answer, m.index, 200).toLowerCase();
    const headerBleed = isTableHeaderBestBleed(answer, m.index);

    // top_pick: preference must refer to SMPL, not a nearby column header.
    const topPickBoundToSmpl =
      !headerBleed &&
      (/\b(top\s*pick|top\s*choice|standout|clearest(?:\s+match)?|strongest(?:\s+candidate)?)\b/i.test(
        sentence,
      ) ||
        (/\bbest\b/i.test(sentence) &&
          /\bsmpl(?:\.ai)?\b/i.test(sentence) &&
          !/\bbest\s+fit\b/i.test(sentence) &&
          peersInText(sentence) === 0));

    if (
      topPickBoundToSmpl &&
      (/\bsmpl(?:\.ai)?\b[^.!?]{0,80}\b(best|top\s*pick|standout|clearest|strongest)\b/i.test(
        sentence,
      ) ||
        /\b(best|top\s*pick|standout|clearest|strongest)[^.!?]{0,80}\bsmpl(?:\.ai)?\b/i.test(
          sentence,
        ) ||
        /\b(my\s+(?:top\s+)?recommendation|i(?:'d|\s+would)\s+(?:pick|choose|go\s+with))\b[^.!?]{0,60}\bsmpl(?:\.ai)?\b/i.test(
          sentence,
        ))
    ) {
      strength = maxStrength(strength, "top_pick");
      continue;
    }

    // recommended: SMPL-specific advice (not a multi-vendor start list).
    const recommendCue =
      /\b(recommend(?:ed|ing)?|good\s+fit|worth\s+evaluating|strong\s+option|investigate\s+it|i(?:'d|\s+would)\s+investigate)\b/i.test(
        sentence,
      ) ||
      /\b(recommend(?:ed|ing)?|good\s+fit|worth\s+evaluating|strong\s+option)\b/i.test(
        win,
      );
    if (recommendCue && /\bsmpl(?:\.ai)?\b/i.test(sentence)) {
      const peers = peersInText(sentence);
      if (
        peers <= 1 ||
        /\b(investigate\s+it|i(?:'d|\s+would)\s+investigate|recommend\s+smpl|smpl[^.!?]{0,40}recommend)\b/i.test(
          sLower,
        )
      ) {
        strength = maxStrength(strength, "recommended");
        continue;
      }
      strength = maxStrength(strength, "shortlisted");
      continue;
    }

    // shortlisted: option / look-at / shortlist cues in the SMPL sentence.
    if (
      /\b(shortlist|alternatives?|options?|include[sd]?|also\s+look|worth\s+looking|newer\s+option|start(?:ing)?\s+(?:the\s+)?evaluation|consider)\b/i.test(
        sLower,
      )
    ) {
      strength = maxStrength(strength, "shortlisted");
    }
  }

  return { strength, explicit_rank, variants };
}

function competitorStrength(
  answer: string,
  name: string,
): CompetitorEval {
  const re = new RegExp(`\\b${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
  const m = re.exec(answer);
  if (!m) {
    return {
      name,
      mentioned: false,
      recommendation_strength: "none",
      explicit_rank: null,
    };
  }
  const ctx = windowAround(answer, m.index).toLowerCase();
  let explicit_rank: number | null = null;
  const ranked = answer.match(
    new RegExp(
      `(?:^|\\n)\\s*(\\d+)[.)]\\s*[^\\n]{0,80}${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`,
      "i",
    ),
  );
  if (ranked) {
    const n = Number(ranked[1]);
    if (n >= 1 && n <= 20) explicit_rank = n;
  }
  let strength: RecommendationStrength = "mentioned";
  if (/\b(best|top\s*pick|leader)\b/.test(ctx) || explicit_rank === 1) {
    strength = "top_pick";
  } else if (/\b(recommend|strong\s+option|consider)\b/.test(ctx)) {
    strength = "recommended";
  } else if (/\b(shortlist|alternatives?|options?)\b/.test(ctx)) {
    strength = "shortlisted";
  }
  return {
    name,
    mentioned: true,
    recommendation_strength: strength,
    explicit_rank,
  };
}

function normalizeUrl(raw: string): string | null {
  try {
    const u = new URL(raw.trim());
    if (!/^https?:$/i.test(u.protocol)) return null;
    return u.href;
  } catch {
    return null;
  }
}

/**
 * Rules-based evaluator. Brand truth is used only here — never in discovery prompts.
 */
export function evaluateManualAudit(input: {
  query: string;
  answer: string;
  citationUrls?: string[];
  competitors?: string[];
}): AioEvaluation {
  const answer = input.answer || "";
  const citations = unique(
    (input.citationUrls || [])
      .map(normalizeUrl)
      .filter((x): x is string => Boolean(x)),
  );
  // Also harvest URLs from the pasted answer
  const fromBody = [...answer.matchAll(/https?:\/\/[^\s)\]>"']+/gi)].map((m) =>
    normalizeUrl(m[0].replace(/[.,;]+$/, "")),
  );
  const allUrls = unique([
    ...citations,
    ...fromBody.filter((x): x is string => Boolean(x)),
  ]);

  const smpl = classifySmplStrength(answer);
  const smpl_mentioned = smpl.strength !== "none";
  const owned = allUrls.filter((u) => /smpl-ai\.com/i.test(u));
  const smpl_owned_domain_cited = owned.length > 0;
  const smpl_cited =
    smpl_owned_domain_cited ||
    allUrls.some((u) => /smpl/i.test(u)) ||
    (smpl_mentioned && /\[\d+\]|source|cite/i.test(answer));

  const competitors = (input.competitors?.length
    ? input.competitors
    : [...DEFAULT_COMPETITORS]
  ).map((name) => competitorStrength(answer, name));

  const incorrect: string[] = [];
  if (smpl_mentioned) {
    for (const { re, label } of UNVERIFIED_CLAIM_PATTERNS) {
      // only flag if claim appears near an SMPL mention window
      for (const reS of SMPL_PATTERNS) {
        reS.lastIndex = 0;
        const m = reS.exec(answer);
        if (m && re.test(windowAround(answer, m.index, 220))) {
          incorrect.push(label);
          break;
        }
      }
    }
  }

  const lower = answer.toLowerCase();
  const hits = GOOD_POSITIONING.filter((k) => lower.includes(k)).length;
  let positioning = smpl_mentioned
    ? Math.min(1, 0.35 + hits * 0.08)
    : 0;
  if (incorrect.length) {
    positioning = Math.max(0, positioning - 0.15 * incorrect.length);
  }
  // Prefer SaaS FP&A associations over generic "AI tool"
  if (smpl_mentioned && /\bai\s+tool\b/i.test(answer) && hits < 2) {
    positioning = Math.max(0, positioning - 0.2);
  }

  const queryTokens = input.query
    .toLowerCase()
    .split(/\W+/)
    .filter((t) => t.length > 3);
  const overlap = queryTokens.filter((t) => lower.includes(t)).length;
  const answer_relevance =
    queryTokens.length === 0
      ? 0.5
      : Math.min(1, overlap / Math.min(8, queryTokens.length));

  const positioning_summary = smpl_mentioned
    ? `Matched ${hits} desired positioning terms; ${incorrect.length} unverified-claim flags.`
    : "SMPL not mentioned.";

  return {
    smpl_mentioned,
    smpl_name_variants_found: smpl.variants,
    recommendation_strength: smpl.strength,
    explicit_rank: smpl.explicit_rank,
    prominence_score: strengthWeight(smpl.strength),
    smpl_cited,
    smpl_owned_domain_cited,
    smpl_cited_urls: owned,
    competitors: competitors.filter((c) => c.mentioned),
    positioning_accuracy: Number(positioning.toFixed(2)),
    positioning_summary,
    incorrect_or_unverified_claims: unique(incorrect),
    answer_relevance: Number(answer_relevance.toFixed(2)),
    notes: `Evaluator ${EVALUATOR_VERSION}; brand=${brandTruth.brand.canonical_name}`,
  };
}
