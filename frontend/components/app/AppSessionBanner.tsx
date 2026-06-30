"use client";

import Link from "next/link";
import { signOut } from "next-auth/react";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { hasModule, planLabel as formatPlanLabel } from "@/lib/entitlements/plan-modules";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export function AppSessionBanner() {
  const { email, organizationId, organizations, isLoading } = useActiveOrganization();
  const activeOrg = organizations.find((org) => org.id === organizationId);
  const orgName = activeOrg?.name ?? organizationId;
  const planName = activeOrg ? formatPlanLabel(activeOrg.plan) : null;
  const showBoard = activeOrg && hasModule(activeOrg.enabledModules, activeOrg.plan, "board_export");
  const showForecast = activeOrg && hasModule(activeOrg.enabledModules, activeOrg.plan, "forecast_engine");
  const showOps = isSmplOpsAdminEmail(email);

  if (isLoading) {
    return (
      <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>
        Loading workspace session...
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        marginBottom: 8,
        fontSize: 13,
        color: "var(--muted)",
      }}
    >
      <span>
        Signed in as <strong style={{ color: "var(--text)" }}>{email || "unknown"}</strong>
        {orgName ? (
          <>
            {" "}
            · Workspace: <strong style={{ color: "var(--text)" }}>{orgName}</strong>
          </>
        ) : null}
        {planName ? (
          <>
            {" "}
            · Plan: <strong style={{ color: "var(--text)" }}>{planName}</strong>
          </>
        ) : null}
      </span>
      <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <Link href="/app/workspace" style={{ color: "var(--muted)", fontSize: 13 }}>
          Workspace
        </Link>
        {showBoard ? (
          <Link href="/app/board" style={{ color: "var(--muted)", fontSize: 13 }}>
            Board Platform
          </Link>
        ) : null}
        {showForecast ? (
          <Link href="/forecast-engine" style={{ color: "var(--muted)", fontSize: 13 }}>
            Forecast Engine
          </Link>
        ) : null}
        {showOps ? (
          <Link href="/app/ops" style={{ color: "var(--muted)", fontSize: 13 }}>
            SMPL Ops
          </Link>
        ) : null}
        <button
        type="button"
        onClick={() => signOut({ callbackUrl: "/login" })}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          color: "var(--muted)",
          cursor: "pointer",
          fontSize: 13,
        }}
      >
        Sign out
      </button>
      </span>
    </div>
  );
}
