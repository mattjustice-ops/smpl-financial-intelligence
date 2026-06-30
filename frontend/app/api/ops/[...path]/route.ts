import { NextRequest } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { proxyToBackend } from "@/lib/backendProxy";

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: RouteContext) {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) {
    return access.error;
  }

  const { path } = await context.params;
  const suffix = path.join("/");
  return proxyToBackend(request, `/api/v1/ops/${suffix}`);
}

export async function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
