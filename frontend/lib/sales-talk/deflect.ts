/** Default when the question is about product/behavior, not a locked number. */
export const DEFLECT_PRODUCT_BEHAVIOR =
  "Good question — I want to confirm the precise product behavior and follow up right after this rather than guess.";

/** Default only when the question is clearly asking for a locked commercial figure. */
export const DEFLECT_EXACT_FIGURE =
  "Good question — I want to give you an exact figure rather than guess, so let me follow up right after this.";

const FIGURE_QUESTION_RE =
  /\b(tam|sam|som|acv|pricing|price point|how much (do you|does it) (cost|charge)|what('?s| is) your (price|pricing)|funding|how much have you raised|valuation|runway|round size)\b/i;

/**
 * Context-aware fallback deflect for uncovered questions.
 * Figure language is reserved for pricing/TAM/funding-style asks;
 * everything else uses product-behavior language (never "exact figure").
 */
export function pickDeflectScript(question: string): string {
  if (FIGURE_QUESTION_RE.test(question)) return DEFLECT_EXACT_FIGURE;
  return DEFLECT_PRODUCT_BEHAVIOR;
}
