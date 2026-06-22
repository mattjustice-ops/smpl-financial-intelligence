import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

/** Outlook payload can exceed Vercel's default serverless timeout on cold Neon queries. */
export const maxDuration = 300;

export async function GET(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/reporting/outlook");
}
