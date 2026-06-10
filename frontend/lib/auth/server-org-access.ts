import "server-only";

import type { Session } from "next-auth";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";

export function organizationIdFromRequest(request: NextRequest): string | null {
  const fromQuery = request.nextUrl.searchParams.get("organization_id")?.trim();
  if (fromQuery) return fromQuery;

  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentType = request.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      // Body is consumed by proxy caller when needed; org check uses query for now.
    }
  }
  return null;
}

export function canAccessOrganization(session: Session, organizationId: string): boolean {
  if (session.user?.activeOrganizationId === organizationId) {
    return true;
  }
  return (
    session.user?.organizations?.some((org) => org.organizationId === organizationId) ?? false
  );
}

export async function requireAuthenticatedSession():
  Promise<{ session: Session } | { error: NextResponse }> {
  const session = await auth();
  if (!session?.user?.email) {
    return { error: NextResponse.json({ detail: "Unauthorized" }, { status: 401 }) };
  }
  return { session };
}

export async function requireOrganizationAccess(
  request: NextRequest,
): Promise<{ session: Session; organizationId: string | null } | { error: NextResponse }> {
  const authResult = await requireAuthenticatedSession();
  if ("error" in authResult) {
    return authResult;
  }

  const organizationId = organizationIdFromRequest(request);
  if (!organizationId) {
    return { session: authResult.session, organizationId: null };
  }

  if (!canAccessOrganization(authResult.session, organizationId)) {
    return {
      error: NextResponse.json(
        { detail: "You do not have access to this organization." },
        { status: 403 },
      ),
    };
  }

  return { session: authResult.session, organizationId };
}
