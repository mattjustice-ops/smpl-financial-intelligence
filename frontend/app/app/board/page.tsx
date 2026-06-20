"use client";

import Link from "next/link";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

export default function BoardPlatformPage() {
  const { organizationId, isLoading: orgLoading } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const canView = hasModule("board_export");

  if (orgLoading) {
    return (
      <div style={{ minHeight: "100vh", background: "#18241b", color: "#aab8a2", padding: 24 }}>
        Loading session…
      </div>
    );
  }

  if (!canView) {
    return (
      <div style={{ minHeight: "100vh", background: "#18241b", color: "#dde8d6", padding: 24 }}>
        <h1>Board Platform</h1>
        <p style={{ color: "#aab8a2" }}>
          Board Platform requires the board_export entitlement ({planLabel} plan).{" "}
          <Link href="/app" style={{ color: "#c4855a" }}>
            Back to operating system
          </Link>
        </p>
      </div>
    );
  }

  const src = organizationId
    ? `/board/index.html?embedded=1&organization_id=${encodeURIComponent(organizationId)}`
    : "/board/index.html?embedded=1";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#18241b" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          borderBottom: "1px solid #2e3f31",
          fontSize: 12,
          color: "#72826a",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <span>Board Platform · org {organizationId || "—"}</span>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link href="/forecast-engine" style={{ color: "#c4855a", textDecoration: "none" }}>
            Forecast Engine
          </Link>
          <Link href="/app" style={{ color: "#c4855a", textDecoration: "none" }}>
            Operating OS
          </Link>
        </div>
      </div>
      <iframe title="SMPL Board Platform" src={src} style={{ flex: 1, width: "100%", border: "none" }} />
    </div>
  );
}
