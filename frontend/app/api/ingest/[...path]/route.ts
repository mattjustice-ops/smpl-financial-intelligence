import { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const suffix = path.join("/");
  return proxyToBackendAuthed(request, `/api/v1/ingest/${suffix}`);
}

export async function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
