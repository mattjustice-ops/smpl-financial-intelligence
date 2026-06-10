import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

type RouteContext = { params: { path: string[] } };

function apiPath(segments: string[]): string {
  return `/api/v1/${segments.join("/")}`;
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, apiPath(context.params.path));
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, apiPath(context.params.path));
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, apiPath(context.params.path));
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, apiPath(context.params.path));
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyToBackendAuthed(request, apiPath(context.params.path));
}
