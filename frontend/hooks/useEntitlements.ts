"use client";

import { useMemo } from "react";

import {
  hasModule,
  modulesForPlan,
  normalizePlan,
  OPERATING_SECTIONS,
  planLabel,
  type FeatureModuleId,
  type OperatingModuleId,
} from "@/lib/entitlements/plan-modules";

import { useActiveOrganization } from "./useActiveOrganization";

export function useEntitlements() {
  const { organizationId, organizations, isLoading } = useActiveOrganization();

  const activeOrg = useMemo(
    () => organizations.find((org) => org.id === organizationId),
    [organizations, organizationId],
  );

  const plan = activeOrg?.plan ?? "starter";
  const normalizedPlan = normalizePlan(plan);
  const enabledModules = useMemo(() => {
    if (activeOrg?.enabledModules && activeOrg.enabledModules.length > 0) {
      return activeOrg.enabledModules;
    }
    return modulesForPlan(plan);
  }, [activeOrg?.enabledModules, plan]);

  const entitledSections = useMemo(
    () => OPERATING_SECTIONS.filter((section) => hasModule(enabledModules, plan, section.id)),
    [enabledModules, plan],
  );

  const checkModule = (moduleId: FeatureModuleId) =>
    hasModule(enabledModules, plan, moduleId);

  return {
    plan: normalizedPlan,
    planLabel: planLabel(plan),
    enabledModules,
    entitledSections,
    hasModule: checkModule,
    isLoading,
  };
}

export type { OperatingModuleId, FeatureModuleId };
