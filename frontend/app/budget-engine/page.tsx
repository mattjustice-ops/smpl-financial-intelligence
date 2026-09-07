"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import {
  EmbeddedModuleChrome,
  EmbeddedModuleNavLink,
} from "@/components/app/EmbeddedModuleChrome";
import { useEntitlements } from "@/hooks/useEntitlements";

function BudgetEngineInner() {
  const { hasModule, planLabel } = useEntitlements();
  const canUse = hasModule("forecast_engine");
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab");

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

  // Bust CDN/browser cache so /app picks up Budget Engine HTML after deploy.
  const tabQ = tab ? `&tab=${encodeURIComponent(tab)}` : "";
  const src = `/budget-engine/index.html?embedded=1&v=26${tabQ}`;

  return (
    <EmbeddedModuleChrome
      moduleTitle="Budget Engine"
      links={
        <>
          <EmbeddedModuleNavLink href="/budget-engine?tab=analytics">
            Plan Assurance →
          </EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/app/board">Board Platform →</EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/forecast-engine">Forecast Engine →</EmbeddedModuleNavLink>
        </>
      }
    >
      <iframe title="SMPL Budget Engine" src={src} />
    </EmbeddedModuleChrome>
  );
}

export default function BudgetEnginePage() {
  return (
    <Suspense
      fallback={<div className="embedded-module__gate">Loading Budget Engine…</div>}
    >
      <BudgetEngineInner />
    </Suspense>
  );
}
