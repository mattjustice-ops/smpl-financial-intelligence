/**
 * Monthly usage caps — keep aligned with backend/app/services/ops/usage_limits.py
 */

export type UsageLimitKey = "ai_cost_usd_monthly" | "exports_monthly" | "llm_calls_monthly";

export type PlanUsageLimits = Record<UsageLimitKey, number | null>;

/** Flat caps for every plan (no tiered ranges). */
export const DEFAULT_USAGE_LIMITS: PlanUsageLimits = {
  ai_cost_usd_monthly: 10,
  exports_monthly: 10,
  llm_calls_monthly: 10,
};

export function usageLimitsForPlan(_plan: string | null | undefined): PlanUsageLimits {
  return { ...DEFAULT_USAGE_LIMITS };
}

export function formatUsageLimitLabel(key: UsageLimitKey): string {
  switch (key) {
    case "ai_cost_usd_monthly":
      return "AI spend / month";
    case "exports_monthly":
      return "Exports / month";
    case "llm_calls_monthly":
      return "LLM calls / month";
    default:
      return key;
  }
}
