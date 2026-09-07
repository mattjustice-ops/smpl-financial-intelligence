"use client";

import Link from "next/link";

import {
  EmbeddedModuleChrome,
  EmbeddedModuleNavLink,
} from "@/components/app/EmbeddedModuleChrome";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function ForecastEnginePage() {
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

  // Cache-bust so /app picks up Forecast HTML after demo-cut deploy.
  const src = "/forecast-engine/index.html?embedded=1&v=3";

  return (
    <EmbeddedModuleChrome
      moduleTitle="Forecast Engine"
      links={
        <>
          <EmbeddedModuleNavLink href="/budget-engine?tab=analytics">
            Plan Assurance →
          </EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/app/board">Board Platform →</EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/budget-engine">Budget Engine →</EmbeddedModuleNavLink>
        </>
      }
    >
      <iframe title="SMPL Forecast Engine" src={src} />
    </EmbeddedModuleChrome>
  );
}
