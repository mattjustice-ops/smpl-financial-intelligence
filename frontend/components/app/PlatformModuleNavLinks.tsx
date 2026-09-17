"use client";

import { EmbeddedModuleNavLink } from "@/components/app/EmbeddedModuleChrome";

/**
 * Shared module chrome links, most-used first.
 * Board Platform stays reachable after Validation (validate → present).
 */
export function PlatformModuleNavLinks() {
  return (
    <>
      <EmbeddedModuleNavLink href="/app/workspace">Workspace</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/app/board?view=validation">Validation Engine</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/forecast-engine">Forecast Engine</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/budget-engine">Budget Engine</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/app/board">Board Platform</EmbeddedModuleNavLink>
    </>
  );
}
