"use client";

import Link from "next/link";
import { signOut } from "next-auth/react";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { hasModule, planLabel as formatPlanLabel } from "@/lib/entitlements/plan-modules";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

type AppSessionBannerProps = {
  /**
   * Module jump links under the identity line.
   * Off inside EmbeddedModuleChrome (top bar already has them).
   */
  showModuleLinks?: boolean;
};

export function AppSessionBanner({ showModuleLinks = false }: AppSessionBannerProps) {
  const { email, organizationId, organizations, isLoading } = useActiveOrganization();
  const activeOrg = organizations.find((org) => org.id === organizationId);
  const orgName = activeOrg?.name ?? organizationId;
  const planName = activeOrg ? formatPlanLabel(activeOrg.plan) : null;
  const showBoard = activeOrg && hasModule(activeOrg.enabledModules, activeOrg.plan, "board_export");
  const showForecast = activeOrg && hasModule(activeOrg.enabledModules, activeOrg.plan, "forecast_engine");
  const showOps = isSmplOpsAdminEmail(email);

  if (isLoading) {
    return <div className="app-session-banner">Loading workspace session…</div>;
  }

  return (
    <div className="app-session-banner">
      <span>
        Signed in as <strong>{email || "unknown"}</strong>
        {orgName ? (
          <>
            {" "}
            · Workspace: <strong>{orgName}</strong>
          </>
        ) : null}
        {planName ? (
          <>
            {" "}
            · Plan: <strong>{planName}</strong>
          </>
        ) : null}
      </span>
      <span className="app-session-banner__actions">
        {showModuleLinks ? (
          <>
            {showBoard ? <Link href="/app/board">Board Platform</Link> : null}
            <Link href="/app/workspace">Workspace</Link>
            {showForecast ? <Link href="/forecast-engine">Forecast Engine</Link> : null}
            {showOps ? <Link href="/app/ops">SMPL Ops</Link> : null}
          </>
        ) : null}
        <button
          type="button"
          className="app-session-banner__signout"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          Sign out
        </button>
      </span>
    </div>
  );
}
