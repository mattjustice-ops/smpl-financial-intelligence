import { NextRequest, NextResponse } from "next/server";

import { requireOrganizationAccess } from "@/lib/auth/server-org-access";
import { backendBaseUrl } from "@/lib/billing/backend-client";

export function backendUrl(): string {
  return backendBaseUrl() ?? "http://127.0.0.1:8000";
}

/** Server-side proxy from Next to FastAPI (avoids rewrite / CORS issues). */
export async function proxyToBackend(
  request: NextRequest,
  apiPath: string,
): Promise<NextResponse> {
  const search = request.nextUrl.search;
  const url = `${backendUrl()}${apiPath}${search}`;
  const method = request.method.toUpperCase();
  try {
    const headers: Record<string, string> = {};
    const internalKey = process.env.BILLING_INTERNAL_API_KEY?.trim();
    if (internalKey) {
      headers["X-Billing-Internal-Key"] = internalKey;
    }

    const init: RequestInit = { cache: "no-store", method, headers };
    if (method !== "GET" && method !== "HEAD") {
      init.body = await request.arrayBuffer();
      const contentType = request.headers.get("content-type");
      if (contentType) {
        headers["Content-Type"] = contentType;
      }
    }
    const res = await fetch(url, init);
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
        "X-SFI-Proxy-Target": url,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      {
        detail: `Proxy failed: ${message}`,
        proxy_target: url,
        hint: "Check SFI_BACKEND_URL and Railway API health.",
      },
      { status: 502 },
    );
  }
}

/** Requires login; enforces organization_id membership when present in query. */
export async function proxyToBackendAuthed(
  request: NextRequest,
  apiPath: string,
): Promise<NextResponse> {
  const access = await requireOrganizationAccess(request);
  if ("error" in access) {
    return access.error;
  }
  return proxyToBackend(request, apiPath);
}
