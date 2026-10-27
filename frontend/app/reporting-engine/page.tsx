"use client";

import Link from "next/link";

import { EmbeddedModuleChrome } from "@/components/app/EmbeddedModuleChrome";
import { PlatformModuleNavLinks } from "@/components/app/PlatformModuleNavLinks";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function ReportingEnginePage() {
  const { hasModule, planLabel } = useEntitlements();
  const canUse = hasModule("board_export");

  if (!canUse) {
    return (
      <div className="embedded-module__gate">
        <h1>Reporting Engine</h1>
        <p>
          Reporting Engine requires the board_export entitlement ({planLabel} plan).{" "}
          <Link href="/app/board">Back to Board Platform</Link>
        </p>
      </div>
    );
  }

  const src = "/reporting-engine/index.html?embedded=1&v=30";

  return (
    <EmbeddedModuleChrome moduleTitle="Reporting Engine" links={<PlatformModuleNavLinks />}>
      <iframe title="SMPL Reporting Engine" src={src} />
    </EmbeddedModuleChrome>
  );
}
