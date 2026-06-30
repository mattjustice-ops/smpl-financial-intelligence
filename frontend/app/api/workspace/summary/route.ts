import { NextRequest, NextResponse } from "next/server";

import { requireOrganizationAccess } from "@/lib/auth/server-org-access";
import { backendUrl } from "@/lib/backendProxy";
import { DEFAULT_USAGE_LIMITS } from "@/lib/entitlements/usage-limits";

function backendHeaders(userId: string | null | undefined): Record<string, string> {
  const headers: Record<string, string> = { "Cache-Control": "no-cache" };
  const internalKey = process.env.BILLING_INTERNAL_API_KEY?.trim();
  if (internalKey) {
    headers["X-Billing-Internal-Key"] = internalKey;
  }
  if (userId?.trim()) {
    headers["X-SFI-User-Id"] = userId.trim();
  }
  return headers;
}

function emptyCloseLedger() {
  return {
    period: { kind: "rolling_days" as const, days: 30 },
    ingest_by_source: {},
    event_totals: {},
    recent_row_errors: [],
    recent_batches: [],
  };
}

/** Workspace summary — proxies Railway; falls back to usage API until workspace is deployed. */
export async function GET(request: NextRequest) {
  const access = await requireOrganizationAccess(request);
  if ("error" in access) {
    return access.error;
  }

  const organizationId = access.organizationId;
  if (!organizationId) {
    return NextResponse.json({ detail: "organization_id query parameter is required." }, { status: 400 });
  }

  const base = backendUrl();
  if (!base) {
    return NextResponse.json({ detail: "SFI_BACKEND_URL is not configured." }, { status: 502 });
  }

  const search = request.nextUrl.search;
  const headers = backendHeaders(access.session.user?.id);
  const workspaceUrl = `${base}/api/v1/workspace/summary${search}`;

  try {
    const workspaceRes = await fetch(workspaceUrl, { cache: "no-store", headers });
    if (workspaceRes.ok) {
      const text = await workspaceRes.text();
      return new NextResponse(text, {
        status: workspaceRes.status,
        headers: {
          "Content-Type": workspaceRes.headers.get("content-type") || "application/json",
        },
      });
    }

    if (workspaceRes.status !== 404) {
      const text = await workspaceRes.text();
      return new NextResponse(text, {
        status: workspaceRes.status,
        headers: {
          "Content-Type": workspaceRes.headers.get("content-type") || "application/json",
        },
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ detail: `Workspace proxy failed: ${message}` }, { status: 502 });
  }

  const usageUrl = `${base}/api/v1/usage/monthly-status?organization_id=${encodeURIComponent(organizationId)}`;
  const usageRes = await fetch(usageUrl, { cache: "no-store", headers });
  if (!usageRes.ok) {
    const detail = await usageRes.text();
    return NextResponse.json(
      {
        detail: "Workspace API is not deployed yet and usage fallback failed.",
        workspace_status: 404,
        usage_status: usageRes.status,
        usage_detail: detail,
        hint: "Push latest backend to Railway and run workspace_001 migration on Neon.",
      },
      { status: 502 },
    );
  }

  const usage = (await usageRes.json()) as Record<string, unknown>;
  const org = access.session.user?.organizations?.find(
    (row) => row.organizationId === organizationId,
  );

  return NextResponse.json({
    organization_id: organizationId,
    organization_name: org?.organizationName ?? organizationId,
    plan: org?.plan ?? null,
    generated_at: new Date().toISOString(),
    available_months: [],
    plan_limits: DEFAULT_USAGE_LIMITS,
    usage,
    storage: {
      warehouse_rows: 0,
      estimated_storage_mb: 0,
    },
    close_ledger: emptyCloseLedger(),
    _fallback: true,
    _fallback_reason: "Railway API does not expose /api/v1/workspace yet — showing usage only.",
  });
}
