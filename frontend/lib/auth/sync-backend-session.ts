import "server-only";

import { backendBaseUrl, callBillingBackend } from "@/lib/billing/backend-client";

import type { BackendOrganization } from "./types";

export type { BackendOrganization } from "./types";

export type SessionSyncResult =
  | {
      ok: true;
      data: {
        userId: string;
        email: string;
        name: string | null;
        activeOrganizationId: string;
        organizations: BackendOrganization[];
      };
    }
  | { ok: false; code?: string; message: string };

export async function syncBackendSession(input: {
  email: string;
  name?: string | null;
  authSubject?: string | null;
}): Promise<SessionSyncResult> {
  try {
    const res = await callBillingBackend("/api/v1/auth/session-sync", {
      method: "POST",
      body: {
        email: input.email,
        name: input.name ?? null,
        auth_subject: input.authSubject ?? null,
      },
    });

    const payload = (await res.json()) as Record<string, unknown> & {
      detail?: { code?: string; message?: string } | string;
    };

    if (!res.ok) {
      const detail = payload.detail;
      if (detail && typeof detail === "object" && "message" in detail) {
        return { ok: false, code: detail.code, message: String(detail.message) };
      }
      return {
        ok: false,
        message: typeof detail === "string" ? detail : "Could not sync your workspace access.",
      };
    }

    return {
      ok: true,
      data: {
        userId: String(payload.userId),
        email: String(payload.email),
        name: payload.name ? String(payload.name) : null,
        activeOrganizationId: String(payload.activeOrganizationId),
        organizations: (payload.organizations as BackendOrganization[]) ?? [],
      },
    };
  } catch (error) {
    if (error instanceof Error && /fetch failed|ECONNREFUSED|ENOTFOUND/i.test(error.message)) {
      const api = backendBaseUrl() ?? "http://127.0.0.1:8001";
      return {
        ok: false,
        message: `Cannot reach the SMPL API at ${api}. Start the backend on port 8001, then request a fresh sign-in link.`,
      };
    }
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Backend session sync failed.",
    };
  }
}
