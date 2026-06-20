import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

/** Board payload can exceed Vercel's default 60s proxy window. */
export const maxDuration = 300;

export async function GET(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/board-platform/payload");
}
