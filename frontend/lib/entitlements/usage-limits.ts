/**
 * Plan usage caps — keep aligned with backend/app/services/ops/usage_limits.py
 */

import type { PricingTierId } from "@/lib/billing/plans";
import { normalizePlan } from "@/lib/entitlements/plan-modules";

export type UsageLimitKey = "ai_cost_usd_monthly" | "exports_monthly" | "llm_calls_monthly";

export type PlanUsageLimits = Record<UsageLimitKey, number | null>;

const PLAN_USAGE_LIMITS: Record<PricingTierId, PlanUsageLimits> = {
  starter: {
    ai_cost_usd_monthly: 25,
    exports_monthly: 10,
    llm_calls_monthly: 100,
  },
  professional: {
    ai_cost_usd_monthly: 100,
    exports_monthly: 50,
    llm_calls_monthly: 500,
  },
  enterprise: {
    ai_cost_usd_monthly: null,
    exports_monthly: null,
    llm_calls_monthly: null,
  },
};

export function usageLimitsForPlan(plan: string | null | undefined): PlanUsageLimits {
  return PLAN_USAGE_LIMITS[normalizePlan(plan)];
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
