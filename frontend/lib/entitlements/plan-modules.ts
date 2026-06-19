/**
 * Plan module entitlements — keep aligned with backend/app/services/entitlements.py
 */

import type { PricingTierId } from "@/lib/billing/plans";

export type OperatingModuleId =
  | "executive"
  | "arr"
  | "revenue"
  | "management-pl"
  | "workforce"
  | "gtm"
  | "pipeline"
  | "cash"
  | "decisions";

export type FeatureModuleId = OperatingModuleId | "board_export" | "ai_commentary" | "forecast_engine";

export const OPERATING_SECTIONS = [
  { id: "executive" as const, label: "Executive Summary" },
  { id: "arr" as const, label: "ARR Waterfall" },
  { id: "revenue" as const, label: "Revenue" },
  { id: "management-pl" as const, label: "Management P&L" },
  { id: "workforce" as const, label: "Workforce" },
  { id: "gtm" as const, label: "GTM / Marketing" },
  { id: "pipeline" as const, label: "Pipeline" },
  { id: "cash" as const, label: "Cash Forecast" },
  { id: "decisions" as const, label: "Risks & Validation" },
];

const STARTER_MODULES: readonly FeatureModuleId[] = [
  "executive",
  "arr",
  "revenue",
  "gtm",
  "pipeline",
  "decisions",
  "board_export",
  "ai_commentary",
];

const PROFESSIONAL_MODULES: readonly FeatureModuleId[] = [
  ...STARTER_MODULES,
  "management-pl",
  "workforce",
  "cash",
];

const ENTERPRISE_MODULES: readonly FeatureModuleId[] = [
  ...PROFESSIONAL_MODULES,
  "forecast_engine",
];

const PLAN_MODULE_MAP: Record<PricingTierId, readonly FeatureModuleId[]> = {
  starter: STARTER_MODULES,
  professional: PROFESSIONAL_MODULES,
  enterprise: ENTERPRISE_MODULES,
};

export function normalizePlan(plan: string | null | undefined): PricingTierId {
  const key = (plan ?? "starter").trim().toLowerCase();
  if (key === "growth") return "professional";
  if (key === "professional" || key === "enterprise" || key === "starter") {
    return key;
  }
  return "starter";
}

export function modulesForPlan(plan: string | null | undefined): FeatureModuleId[] {
  return [...PLAN_MODULE_MAP[normalizePlan(plan)]];
}

export function hasModule(
  enabledModules: readonly string[] | undefined,
  plan: string | null | undefined,
  moduleId: FeatureModuleId,
): boolean {
  const modules = enabledModules?.length ? enabledModules : modulesForPlan(plan);
  return modules.includes(moduleId);
}

export function planLabel(plan: string | null | undefined): string {
  const normalized = normalizePlan(plan);
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

/** Professional-only operating tabs (shown as upgrade hints on Starter). */
export const PROFESSIONAL_ONLY_SECTIONS: OperatingModuleId[] = [
  "management-pl",
  "workforce",
  "cash",
];
