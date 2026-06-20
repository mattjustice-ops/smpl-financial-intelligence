"use client";

import Link from "next/link";

import {
  EmbeddedModuleChrome,
  EmbeddedModuleNavLink,
} from "@/components/app/EmbeddedModuleChrome";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function ForecastEnginePage() {
  const { organizationId } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const canUse = hasModule("forecast_engine");

  if (!canUse) {
    return (
      <div className="embedded-module__gate">
        <h1>SMPL · Rolling Forecast Engine</h1>
        <p>
          Enterprise required ({planLabel}). <Link href="/app">Back to app</Link>
        </p>
      </div>
    );
  }

  const src = organizationId
    ? `/forecast-engine/index.html?organization_id=${encodeURIComponent(organizationId)}`
    : "/forecast-engine/index.html";

  return (
    <EmbeddedModuleChrome
      moduleTitle="Forecast Engine"
      links={<EmbeddedModuleNavLink href="/app/board">Board Platform →</EmbeddedModuleNavLink>}
    >
      <iframe title="SMPL Forecast Engine" src={src} />
    </EmbeddedModuleChrome>
  );
}
