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
  // Too generic alone — causes wrong-card wins ("why your company" → per-org)
  "company",
  "companies",
  "use",
  "using",
  "get",
  "make",
  "need",
  "want",
  "like",
  "thing",
  "things",
  "something",
  "everything",
  "anything",
  "really",
  "actually",
  "basically",
  "please",
  "tell",
  "give",
  "take",
  "come",
  "going",
  "still",
  "already",
  "only",
  "even",
  "much",
  "many",
  "long",
  "until",
  "after",
  "before",
  "once",
  "again",
  "else",
  "own",
  "every",
  "each",
  "other",
  "another",
  "into",
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
  customize: ["custom", "tailored", "configuration", "methodology"],
  custom: ["customize", "tailored"],
  features: ["capabilities", "modules", "included"],
  mda: ["mda", "board", "commentary"],
  "md&a": ["mda", "board"],
  connector: ["connectors", "integration", "sync"],
  connectors: ["connector", "integration", "sync"],
  arr: ["mrr", "waterfall", "nrr", "grr"],
  mrr: ["arr", "waterfall"],
  nrr: ["grr", "retention", "arr"],
  grr: ["nrr", "retention", "arr"],
  moat: ["defensibility", "architecture"],
  differentiator: ["differentiation"],
  differentiation: ["differentiator"],
  defensibility: ["moat"],
  chatgpt: ["llm"],
  powerbi: ["bi"],
  diy: ["build", "ourselves", "internally"],
  ourselves: ["diy", "internally"],
  internally: ["diy", "ourselves"],
  pigment: ["compete-pigment", "anaplan"],
  anaplan: ["compete-anaplan", "pigment"],
  warehouse: ["snowflake", "databricks"],
  hallucinate: ["hallucination", "hallucinations"],
  hallucination: ["hallucinate", "hallucinations"],
  hallucinations: ["hallucinate", "hallucination"],
  accurate: ["accuracy", "hallucination", "deterministic"],
  accuracy: ["accurate", "deterministic"],
  forecast: ["forecasts", "assumptions", "scenarios"],
  forecasts: ["forecast", "assumptions", "scenarios"],
  auditor: ["auditors", "audit", "board", "trust"],
  auditors: ["auditor", "audit", "board"],
  trace: ["traceability", "evidence", "lineage"],
  traceability: ["trace", "evidence", "lineage"],
  export: ["exports", "download", "pptx"],
  exports: ["export", "download"],
  netsuite: ["erp", "schema"],
  smpl: ["smplai"],
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
    "why would we use",
    "why use smpl",
    "why use your",
    "why your company",
    "why would we choose",
    "why choose smpl",
    "why choose you",
    "why buy smpl",
    "why should we use",
    "value proposition",
    "why us",
  ],
  [
    "build ourselves",
    "build it ourselves",
    "build this ourselves",
    "build our own",
    "build internally",
    "why not build",
    "should we build",
    "diy",
    "build vs buy",
    "build versus buy",
    "why can't we build",
    "why cant we build",
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
    "how accurate is ai",
    "ai accuracy",
    "is the ai accurate",
    "how accurate are the numbers",
    "can we trust ai numbers",
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
    "pigment",
    "why not pigment",
    "vs pigment",
    "why you vs pigment",
  ],
  [
    "anaplan",
    "why not anaplan",
    "vs anaplan",
    "why you vs anaplan",
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
  ["after implementation", "what happens after implementation", "post implementation", "once live"],
  ["time to value", "how long until value", "how soon do we see value", "when do we see value"],
  ["bad data", "what if my data is bad", "dirty data", "messy data", "incomplete data"],
  ["netsuite changes", "if netsuite changes", "erp schema change", "source system changes"],
  ["custom objects", "custom object", "salesforce custom objects"],
  ["export everything", "can i export", "export all data", "download everything"],
  ["own warehouse", "my own warehouse", "use our warehouse", "bring our own warehouse", "byow"],
  ["calculate nrr", "calculate grr", "how do you calculate nrr", "how do you calculate grr", "nrr / grr"],
  ["build forecasts", "how do you forecast", "forecast assumptions", "assumptions configurable"],
  ["board trust", "auditors trust", "can the board trust", "can auditors trust"],
  ["trace every calculation", "trace calculations", "traceability", "lineage"],
  ["validate imports", "detect bad data", "import validation", "data validation"],
  ["ai generate commentary", "how does ai generate", "commentary verified", "ai commentary"],
  ["explain variance", "answer executive questions", "executive questions"],
  ["confidence is low", "low confidence", "what if confidence"],
];

/**
 * Intent → preferred entry IDs. When a pattern matches, those IDs get a large
 * boost and competing wrong-card IDs can be penalized. This is the MVP layer
 * that makes paraphrases reliable without embeddings.
 */
type IntentRule = {
  name: string;
  patterns: RegExp[];
  preferIds: string[];
  /** Extra tokens injected into scoring for this intent. */
  expandTokens?: string[];
  penalizeIds?: string[];
};

const INTENT_RULES: IntentRule[] = [
  {
    name: "moat",
    patterns: [
      /\bmoat\b/i,
      /\bcompetitive advantage\b/i,
      /\bhard to copy\b/i,
      /\bdefensib/i,
      /\bis ai your advantage\b/i,
    ],
    preferIds: ["architecture-as-moat"],
    expandTokens: ["moat", "defensibility", "competitive", "advantage"],
    penalizeIds: ["implementation-security", "differentiator-three-principles", "system-architecture"],
  },
  {
    name: "why-us",
    patterns: [
      /\bwhy (would|should|do) (we|i) (use|choose|buy|pick)\b/i,
      /\bwhy use (smpl|you|your)\b/i,
      /\bwhy (your|the) company\b/i,
      /\bwhy (choose|pick|buy) (smpl|you)\b/i,
      /\bwhy (would|should) (we|i) (work with|go with)\b/i,
      /\bvalue prop(osition)?\b/i,
      /\bwhy us\b/i,
      /\bwhy (would|should) a customer buy\b/i,
    ],
    preferIds: ["why-us"],
    expandTokens: ["why-us", "value", "proposition", "choose", "smpl"],
    penalizeIds: [
      "per-org-tenant-environment",
      "tenant-isolation",
      "platform-features-overview",
      "team",
    ],
  },
  {
    name: "build-vs-buy",
    patterns: [
      /\bbuild (it |this |that )?(ourselves|our own|internally)\b/i,
      /\bwhy (not|don'?t|do not) (we |i )?(just )?build\b/i,
      /\bshould we build\b/i,
      /\bbuild vs\.? buy\b/i,
      /\bbuild versus buy\b/i,
      /\bdiy\b/i,
      /\bwhy can'?t (we|companies) build\b/i,
      /\bbuild our own\b/i,
    ],
    preferIds: ["build-vs-buy"],
    expandTokens: ["build-vs-buy", "diy", "internally", "ourselves"],
    penalizeIds: ["team", "platform-features-overview", "what-is-smpl"],
  },
  {
    name: "ai-security",
    patterns: [/\bai security\b/i, /\bllm security\b/i, /\bprompt security\b/i],
    preferIds: ["ai-security"],
    expandTokens: ["ai", "security"],
  },
  {
    name: "ai-training",
    patterns: [/\btrain(ing)? (ai |models? )?on (our|customer|my) data\b/i, /\bused for training\b/i],
    preferIds: ["ai-training"],
    expandTokens: ["train", "training", "data"],
  },
  {
    name: "ai-hallucinations",
    patterns: [/\bhallucin/i, /\bmake things up\b/i, /\binvent(ing)? numbers\b/i],
    preferIds: ["ai-hallucinations"],
    expandTokens: ["hallucinate", "hallucinations"],
  },
  {
    name: "ai-accuracy",
    patterns: [
      /\bhow accurate is (the )?ai\b/i,
      /\bai accuracy\b/i,
      /\bis (the )?ai accurate\b/i,
      /\bcan we trust (the )?ai\b/i,
    ],
    preferIds: ["ai-accuracy"],
    expandTokens: ["accuracy", "accurate", "ai"],
    penalizeIds: ["ai-data-handling", "ai-security"],
  },
  {
    name: "system-architecture",
    patterns: [
      /\bsystem architecture\b/i,
      /\btech stack\b/i,
      /\bhow is (it|smpl|the platform) built\b/i,
      /\bapplication architecture\b/i,
      /\bplatform architecture\b/i,
    ],
    preferIds: ["system-architecture"],
    expandTokens: ["system", "architecture", "stack"],
    penalizeIds: ["architecture-as-moat"],
  },
  {
    name: "compete-cube",
    patterns: [/\bcube\b/i],
    preferIds: ["compete-cube"],
    expandTokens: ["cube"],
  },
  {
    name: "compete-pigment",
    patterns: [/\bpigment\b/i],
    preferIds: ["compete-pigment"],
    expandTokens: ["pigment"],
  },
  {
    name: "compete-anaplan",
    patterns: [/\banaplan\b/i],
    preferIds: ["compete-anaplan"],
    expandTokens: ["anaplan"],
  },
  {
    name: "compete-mosaic",
    patterns: [/\bmosaic\b/i, /\bmosiac\b/i, /\bmozaic\b/i, /\bbob finance\b/i],
    preferIds: ["compete-mosaic"],
    expandTokens: ["mosaic"],
  },
  {
    name: "compete-rillet",
    patterns: [/\brillet\b/i],
    preferIds: ["compete-rillet"],
    expandTokens: ["rillet"],
  },
  {
    name: "compete-tableau",
    patterns: [/\btableau\b/i],
    preferIds: ["compete-tableau"],
    expandTokens: ["tableau"],
  },
  {
    name: "compete-power-bi",
    patterns: [/\bpower\s*bi\b/i, /\bpowerbi\b/i],
    preferIds: ["compete-power-bi"],
    expandTokens: ["powerbi"],
  },
  {
    name: "compete-excel",
    patterns: [/\bwhy not (just )?excel\b/i, /\breplace excel\b/i, /\bjust use excel\b/i],
    preferIds: ["compete-excel"],
    expandTokens: ["excel"],
  },
  {
    name: "after-implementation",
    patterns: [
      /\bafter implementation\b/i,
      /\bpost[- ]implementation\b/i,
      /\bonce (we('?re| are) )?live\b/i,
      /\bwhat happens after (go[- ]?live|onboarding|implementation)\b/i,
    ],
    preferIds: ["after-implementation"],
    expandTokens: ["after-implementation", "ongoing", "close"],
    penalizeIds: ["implementation-security", "customization-at-implementation"],
  },
  {
    name: "customize-methodology",
    patterns: [
      /\bcustomize (metrics|arr|methodology|reports?)\b/i,
      /\bdefine arr differently\b/i,
      /\bchange (our )?methodology\b/i,
      /\bour (own )?arr definition\b/i,
      /\bcustom(er)?[- ]specific (metrics|definitions|methodology)\b/i,
    ],
    preferIds: ["customize-metrics-methodology"],
    expandTokens: ["customize", "methodology", "arr", "metrics"],
  },
  {
    name: "time-to-value",
    patterns: [
      /\btime to value\b/i,
      /\bhow long until (we (see|get) )?value\b/i,
      /\bhow soon .{0,20}\bvalue\b/i,
      /\bwhen (do|will) we (see|get) value\b/i,
      /\btime[- ]to[- ]value\b/i,
    ],
    preferIds: ["time-to-value"],
    expandTokens: ["time-to-value", "value", "weeks"],
    penalizeIds: ["dna-pricing", "business-impact"],
  },
  {
    name: "bad-data",
    patterns: [
      /\b(my|our|the) data is bad\b/i,
      /\bbad data\b/i,
      /\bdirty data\b/i,
      /\bmessy data\b/i,
      /\bincomplete data\b/i,
      /\bwhat if .{0,30}\bdata is (bad|wrong|messy|incomplete)\b/i,
    ],
    preferIds: ["data-quality-bad-data"],
    expandTokens: ["bad", "data", "confidence", "incomplete"],
    penalizeIds: ["where-data-stored", "ai-data-handling"],
  },
  {
    name: "netsuite-change",
    patterns: [
      /\bnetsuite changes\b/i,
      /\bif netsuite\b/i,
      /\berp (schema )?changes?\b/i,
      /\bsource system changes\b/i,
      /\bwhen (netsuite|our erp) (changes|updates)\b/i,
    ],
    preferIds: ["netsuite-schema-change"],
    expandTokens: ["netsuite", "schema", "change"],
  },
  {
    name: "custom-objects",
    patterns: [/\bcustom objects?\b/i, /\bsalesforce custom\b/i],
    preferIds: ["custom-objects"],
    expandTokens: ["custom", "objects"],
    penalizeIds: ["customize-reporting-per-customer"],
  },
  {
    name: "export",
    patterns: [
      /\bexport everything\b/i,
      /\bcan i export\b/i,
      /\bexport all\b/i,
      /\bdownload everything\b/i,
      /\bcan we export\b/i,
    ],
    preferIds: ["export-capabilities"],
    expandTokens: ["export", "exports", "download"],
    penalizeIds: ["board-deck-and-mda"],
  },
  {
    name: "replace-boundaries",
    patterns: [
      /\breplace (excel|fp&a|fpa|netsuite|erp|our gl)\b/i,
      /\bdo you replace\b/i,
      /\bare you (a |an )?(excel|fp&a|fpa|netsuite|erp) replacement\b/i,
    ],
    preferIds: ["replace-boundaries"],
    expandTokens: ["replace", "excel", "netsuite", "erp", "fpa"],
  },
  {
    name: "own-warehouse",
    patterns: [
      /\b(my|our|own) warehouse\b/i,
      /\buse (my|our|a) (own )?warehouse\b/i,
      /\bbring (our|my) own warehouse\b/i,
      /\bdo we need a (data )?warehouse\b/i,
      /\bbyow\b/i,
    ],
    preferIds: ["own-warehouse"],
    expandTokens: ["warehouse", "optional"],
    penalizeIds: ["compete-snowflake", "per-org-tenant-environment"],
  },
  {
    name: "nrr-grr",
    patterns: [/\bnrr\b/i, /\bgrr\b/i, /\bnet (dollar )?retention\b/i, /\bgross (revenue )?retention\b/i],
    preferIds: ["nrr-grr-calculation"],
    expandTokens: ["nrr", "grr", "retention"],
    penalizeIds: ["arr-mrr-reporting"],
  },
  {
    name: "forecasts",
    patterns: [
      /\bbuild forecasts?\b/i,
      /\bhow (do you|does) forecast\b/i,
      /\bforecast(ing)? assumptions\b/i,
      /\bassumptions configurable\b/i,
      /\boverride assumptions\b/i,
    ],
    preferIds: ["forecast-assumptions"],
    expandTokens: ["forecast", "assumptions", "scenarios"],
    penalizeIds: ["team"],
  },
  {
    name: "board-auditor-trust",
    patterns: [
      /\b(board|auditors?) trust\b/i,
      /\bcan (the )?(board|auditors?) trust\b/i,
      /\btrust the numbers\b/i,
    ],
    preferIds: ["board-auditor-trust"],
    expandTokens: ["board", "auditor", "trust", "evidence"],
  },
  {
    name: "trace-calculations",
    patterns: [
      /\btrace (every )?calculation\b/i,
      /\btraceability\b/i,
      /\btrace (the )?numbers\b/i,
      /\blineage\b/i,
      /\bhow do i (see|trace|audit) .{0,20}calculation\b/i,
    ],
    preferIds: ["calculation-traceability"],
    expandTokens: ["trace", "evidence", "lineage"],
    penalizeIds: ["determinism"],
  },
  {
    name: "import-validation",
    patterns: [
      /\bvalidate imports?\b/i,
      /\bdetect bad data\b/i,
      /\bimport validation\b/i,
      /\bhow do you validate (imports|data|loads)\b/i,
      /\bdata validation\b/i,
    ],
    preferIds: ["import-validation"],
    expandTokens: ["validate", "import", "validation"],
    penalizeIds: ["confidence-signal", "where-data-stored"],
  },
  {
    name: "ai-commentary",
    patterns: [
      /\bai (generate |generates |write |writes )?commentary\b/i,
      /\bhow does ai generate\b/i,
      /\bcommentary .{0,20}verif/i,
      /\bhow (is|are) .{0,20}commentary verif/i,
    ],
    preferIds: ["ai-commentary-capabilities"],
    expandTokens: ["commentary", "ai", "verified"],
  },
  {
    name: "ai-executive-qa",
    patterns: [
      /\bexplain variance\b/i,
      /\banswer executive questions\b/i,
      /\bai explain variance\b/i,
      /\bexecutive questions\b/i,
    ],
    preferIds: ["ai-executive-qa"],
    expandTokens: ["variance", "executive", "explain"],
  },
  {
    name: "confidence-low",
    patterns: [
      /\bconfidence is low\b/i,
      /\blow confidence\b/i,
      /\bwhat (happens|do you do) if confidence\b/i,
      /\bif confidence is (low|uncertain)\b/i,
    ],
    preferIds: ["confidence-signal"],
    expandTokens: ["confidence", "signal", "low"],
  },
];

function normalizeQuestion(question: string): string {
  return question
    .toLowerCase()
    .replace(/soc\s*2/g, "soc2")
    .replace(/write[\s-]?back/g, "writeback")
    .replace(/power\s*bi/g, "power bi")
    .replace(/chat\s*gpt/g, "chatgpt")
    .replace(/fp\s*&\s*a/g, "fpa")
    .replace(/n\.?\s*r\.?\s*r\.?/g, "nrr")
    .replace(/g\.?\s*r\.?\s*r\.?/g, "grr");
}

export function tokenize(text: string): string[] {
  const base = text
    .toLowerCase()
    .replace(/soc\s*2/g, " soc2 ")
    .replace(/write[\s-]?back/g, " writeback ")
    .replace(/power\s*bi/g, " powerbi ")
    .replace(/chat\s*gpt/g, " chatgpt ")
    .replace(/fp\s*&\s*a/g, " fpa ")
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

function matchingIntents(question: string): IntentRule[] {
  const q = normalizeQuestion(question);
  return INTENT_RULES.filter((rule) => rule.patterns.some((re) => re.test(q)));
}

function tokenizeWithIntents(question: string): string[] {
  const tokens = tokenize(question);
  const seen = new Set(tokens);
  const out = [...tokens];
  for (const intent of matchingIntents(question)) {
    for (const extra of intent.expandTokens ?? []) {
      const t = extra.toLowerCase();
      if (!seen.has(t) && t.length > 1 && !STOP.has(t)) {
        seen.add(t);
        out.push(t);
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
  const q = normalizeQuestion(question);
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

function intentBoost(question: string, entry: SalesKbEntry): number {
  let boost = 0;
  for (const intent of matchingIntents(question)) {
    if (intent.preferIds.includes(entry.id)) {
      boost += 22;
    }
    if (intent.penalizeIds?.includes(entry.id)) {
      boost -= 12;
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
  const tokens = tokenizeWithIntents(question);
  if (tokens.length === 0 && matchingIntents(question).length === 0) return 0;

  let structured =
    fieldScore(tokens, entry.title, 3.2) +
    fieldScore(tokens, (entry.topics ?? []).join(" "), 2.8) +
    fieldScore(tokens, (entry.keywords ?? []).join(" "), 2.4) +
    fieldScore(tokens, entry.id.replace(/-/g, " "), 1.2);

  // Answer body is supporting evidence only — never enough alone to win
  const answerScore = fieldScore(tokens, entry.answer, 0.2);
  const keyBoost = keyPhraseBoost(question, entry);
  const intent = intentBoost(question, entry);

  let score = structured + answerScore + keyBoost + intent + phraseFieldBoost(question, entry);

  // Prefer external_safe slightly when both would match
  if ((entry.tone ?? "external_safe") === "external_safe") {
    score += 0.15;
  }

  // If nothing hit title/topics/keywords/id, collapse weak answer-only matches
  // (unless an intent explicitly preferred this entry)
  if (structured < 0.5 && keyBoost <= 0 && intent <= 0) {
    score *= 0.25;
  }

  // Normalize lightly by query length so short queries aren't drowned
  const denom = Math.sqrt(Math.max(tokens.length, 1));
  return score / denom;
}

export type RetrieveOptions = {
  audience?: SalesAudience | null;
  includeInternalDeep?: boolean;
  limit?: number;
  minScore?: number;
  /** When true, return candidates below minScore for a router shortlist. */
  shortlist?: boolean;
  shortlistLimit?: number;
};

/** Default bar: weak bag-of-words noise deflects instead of wrong-carding. */
export const DEFAULT_MIN_SCORE = 2.4;

export function retrieveSalesAnswers(
  question: string,
  entries: SalesKbEntry[],
  options: RetrieveOptions = {},
): SalesTalkMatch[] {
  const audience = options.audience ?? null;
  const includeInternalDeep = options.includeInternalDeep ?? false;
  const limit = options.limit ?? 3;
  const minScore = options.minScore ?? DEFAULT_MIN_SCORE;
  const shortlist = options.shortlist === true;
  const shortlistLimit = options.shortlistLimit ?? 8;

  const scored: SalesTalkMatch[] = [];
  for (const entry of entries) {
    if (!audienceAllows(entry, audience)) continue;
    if (!toneAllows(entry, includeInternalDeep)) continue;
    const score = scoreEntry(question, entry);
    if (shortlist || score >= minScore) {
      scored.push({ entry, score });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  if (shortlist) {
    return scored.slice(0, shortlistLimit);
  }
  return scored.slice(0, limit);
}

/**
 * Keyword path used when the optional LLM router abstains or is unavailable.
 * Returns [] when top score is below the bar (caller should deflect).
 */
export function keywordBestMatches(
  question: string,
  entries: SalesKbEntry[],
  options: Omit<RetrieveOptions, "shortlist"> = {},
): SalesTalkMatch[] {
  return retrieveSalesAnswers(question, entries, {
    ...options,
    shortlist: false,
    minScore: options.minScore ?? DEFAULT_MIN_SCORE,
  });
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
    "should we",
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
    "why not just build",
    "build it ourselves",
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

/** Exported for verify / debugging. */
export function debugMatchingIntents(question: string): string[] {
  return matchingIntents(question).map((r) => r.name);
}
