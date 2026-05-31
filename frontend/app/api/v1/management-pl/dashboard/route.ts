import type { NextRequest } from "next/server";

import { proxyToBackend } from "../../../../../lib/backendProxy";

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/api/v1/management-pl/dashboard");
}
