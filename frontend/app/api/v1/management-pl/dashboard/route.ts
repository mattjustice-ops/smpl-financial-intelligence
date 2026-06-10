import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "../../../../../lib/backendProxy";

export async function GET(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/management-pl/dashboard");
}
