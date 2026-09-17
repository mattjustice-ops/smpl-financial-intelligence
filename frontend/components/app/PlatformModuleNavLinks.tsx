"use client";

import { EmbeddedModuleNavLink } from "@/components/app/EmbeddedModuleChrome";

/**
 * Shared module chrome links. Board Platform is always first (default landing).
 */
export function PlatformModuleNavLinks() {
  return (
    <>
      <EmbeddedModuleNavLink href="/app/board">Board Platform</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/app/workspace">Workspace</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/app/board?view=validation">Validation Engine</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/forecast-engine">Forecast Engine</EmbeddedModuleNavLink>
      <EmbeddedModuleNavLink href="/budget-engine">Budget Engine</EmbeddedModuleNavLink>
    </>
  );
}
