"use client";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";
import Link from "next/link";

export default function ForecastEnginePage() {
  const { organizationId } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const canUse = hasModule("forecast_engine");

  if (!canUse) {
    return (
      <div style={{ minHeight: "100vh", background: "#18241b", color: "#dde8d6", padding: 24 }}>
        <h1>SMPL · Rolling Forecast Engine</h1>
        <p style={{ color: "#aab8a2" }}>
          Enterprise required ({planLabel}). <Link href="/app">Back to app</Link>
        </p>
      </div>
    );
  }

  const src = organizationId
    ? `/forecast-engine/index.html?organization_id=${encodeURIComponent(organizationId)}`
    : "/forecast-engine/index.html";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#18241b" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "8px 16px",
          borderBottom: "1px solid #2e3f31",
          fontSize: 12,
          color: "#72826a",
        }}
      >
        <span>Live warehouse · org {organizationId || "—"}</span>
        <Link href="/app/board" style={{ color: "#c4855a" }}>
          Board Platform →
        </Link>
      </div>
      <iframe
        title="SMPL Forecast Engine"
        src={src}
        style={{ flex: 1, width: "100%", border: "none" }}
      />
    </div>
  );
}
