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

export const EVALUATOR_VERSION = "rules_v1";

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

function classifySmplStrength(answer: string): {
  strength: RecommendationStrength;
  explicit_rank: number | null;
  variants: string[];
} {
  const variants: string[] = [];
  let firstIdx = -1;
  for (const re of SMPL_PATTERNS) {
    re.lastIndex = 0;
    const m = re.exec(answer);
    if (m) {
      variants.push(m[0]);
      if (firstIdx < 0) firstIdx = m.index;
    }
  }
  if (firstIdx < 0) {
    return { strength: "none", explicit_rank: null, variants: [] };
  }

  const ctx = windowAround(answer, firstIdx).toLowerCase();
  let explicit_rank: number | null = null;
  const ranked = answer.match(
    new RegExp(
      `(?:^|\\n)\\s*(\\d+)[.)]\\s*[^\n]{0,80}(?:SMPL\\.ai|SMPL|smpl-ai\\.com)`,
      "i",
    ),
  );
  if (ranked) {
    const n = Number(ranked[1]);
    if (n >= 1 && n <= 20) explicit_rank = n;
  }

  if (
    /\b(best|top\s*pick|top\s*choice|standout|clearest|strongest)\b/.test(ctx) ||
    explicit_rank === 1
  ) {
    return { strength: "top_pick", explicit_rank, variants: unique(variants) };
  }
  if (
    /\b(recommend|recommended|consider|good\s+fit|worth\s+evaluating|strong\s+option)\b/.test(
      ctx,
    )
  ) {
    return { strength: "recommended", explicit_rank, variants: unique(variants) };
  }
  if (
    /\b(shortlist|alternatives?|options?|include[sd]?|also\s+look)\b/.test(ctx) ||
    (explicit_rank !== null && explicit_rank <= 5)
  ) {
    return { strength: "shortlisted", explicit_rank, variants: unique(variants) };
  }
  return { strength: "mentioned", explicit_rank, variants: unique(variants) };
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
