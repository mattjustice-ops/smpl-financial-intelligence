"use client";

import { signOut } from "next-auth/react";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";

export function AppSessionBanner() {
  const { email, organizationId, organizations, isLoading } = useActiveOrganization();
  const orgName =
    organizations.find((org) => org.id === organizationId)?.name ?? organizationId;

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
      </span>
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
    </div>
  );
}
