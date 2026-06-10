import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "../../../../../lib/backendProxy";

export async function POST(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/workforce/recompute");
}
