"use client";

import Link from "next/link";

import {
  EmbeddedModuleChrome,
  EmbeddedModuleNavLink,
} from "@/components/app/EmbeddedModuleChrome";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function BudgetEnginePage() {
  const { hasModule, planLabel } = useEntitlements();
  const canUse = hasModule("forecast_engine");

  if (!canUse) {
    return (
      <div className="embedded-module__gate">
        <h1>SMPL · Budget Engine</h1>
        <p>
          Enterprise required ({planLabel}). <Link href="/app">Back to app</Link>
        </p>
      </div>
    );
  }

  const src = "/budget-engine/index.html?embedded=1";

  return (
    <EmbeddedModuleChrome
      moduleTitle="Budget Engine"
      links={
        <>
          <EmbeddedModuleNavLink href="/app/board">Board Platform →</EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/forecast-engine">Forecast Engine →</EmbeddedModuleNavLink>
        </>
      }
    >
      <iframe title="SMPL Budget Engine" src={src} />
    </EmbeddedModuleChrome>
  );
}
