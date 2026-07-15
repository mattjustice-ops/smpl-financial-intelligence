import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

/** Trust-strip / close validation can exceed Vercel's default proxy window. */
export const maxDuration = 120;

export async function GET(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/export/validation");
}
