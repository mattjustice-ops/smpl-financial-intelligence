"use client";

import Link from "next/link";

import {
  EmbeddedModuleChrome,
  EmbeddedModuleNavLink,
} from "@/components/app/EmbeddedModuleChrome";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function BoardPlatformPage() {
  const { organizationId, isLoading: orgLoading } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const canView = hasModule("board_export");

  if (orgLoading) {
    return (
      <div className="embedded-module__gate">
        Loading session…
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="embedded-module__gate">
        <h1>Board Platform</h1>
        <p>
          Board Platform requires the board_export entitlement ({planLabel} plan).{" "}
          <Link href="/app">Back to operating system</Link>
        </p>
      </div>
    );
  }

  const src = organizationId
    ? `/board/index.html?embedded=1&organization_id=${encodeURIComponent(organizationId)}`
    : "/board/index.html?embedded=1";

  return (
    <EmbeddedModuleChrome
      moduleTitle="Board Platform"
      links={
        <>
          <EmbeddedModuleNavLink href="/forecast-engine">Forecast Engine</EmbeddedModuleNavLink>
          <EmbeddedModuleNavLink href="/app">Operating OS</EmbeddedModuleNavLink>
        </>
      }
    >
      <iframe title="SMPL Board Platform" src={src} />
    </EmbeddedModuleChrome>
  );
}
