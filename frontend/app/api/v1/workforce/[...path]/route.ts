import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "../../../../../lib/backendProxy";

type RouteContext = { params: { path: string[] } };

function workforcePath(segments: string[]): string {
  return `/api/v1/workforce/${segments.join("/")}`;
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, workforcePath(context.params.path));
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, workforcePath(context.params.path));
}
