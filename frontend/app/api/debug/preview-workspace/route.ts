import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { syncBackendSession } from "@/lib/auth/sync-backend-session";
import { backendBaseUrl } from "@/lib/billing/backend-client";

function hostFromEnv(value: string | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) return null;
  try {
    return new URL(trimmed).host;
  } catch {
    return trimmed;
  }
}

/** Preview/staging diagnostic: workspace + session-sync (no secrets). */
export async function GET() {
  // Block only true production deployments (not Preview branch URLs).
  if (process.env.VERCEL_ENV === "production") {
    return NextResponse.json({ error: "Not available on production" }, { status: 404 });
  }

  const session = await auth();
  const base = backendBaseUrl();
  const email = session?.user?.email ?? null;

  let sync: Awaited<ReturnType<typeof syncBackendSession>> | null = null;
  if (email) {
    sync = await syncBackendSession({
      email,
      name: session?.user?.name ?? null,
      authSubject: session?.user?.id ?? null,
    });
  }

  return NextResponse.json({
    vercel_env: process.env.VERCEL_ENV ?? null,
    sfi_backend_host: hostFromEnv(process.env.SFI_BACKEND_URL),
    next_public_api_host: hostFromEnv(process.env.NEXT_PUBLIC_API_URL),
    backend_host: base ? new URL(base).host : null,
    has_billing_internal_key: Boolean(process.env.BILLING_INTERNAL_API_KEY?.trim()),
    session_email: email,
    session_workspace: session?.user?.activeOrganizationId ?? null,
    session_org_names: (session?.user?.organizations ?? []).map((o) => ({
      id: o.organizationId,
      name: o.organizationName,
    })),
    sync_ok: sync?.ok ?? null,
    sync_workspace: sync?.ok ? sync.data.activeOrganizationId : null,
    sync_org_names: sync?.ok
      ? sync.data.organizations.map((o) => ({
          id: o.organizationId,
          name: o.organizationName,
        }))
      : null,
    sync_error: sync && !sync.ok ? sync.message : null,
    hint:
      base && new URL(base).host.includes("sfi-api-production")
        ? "Preview is calling PRODUCTION API. Run set-vercel-staging-env.ps1, verify-vercel-preview-api-url.ps1, then git push to redeploy."
        : sync && !sync.ok
          ? "If sync_error mentions 401, run scripts/set-vercel-preview-billing-from-production.ps1 and redeploy Preview."
          : null,
  });
}
