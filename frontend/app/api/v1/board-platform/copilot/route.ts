import type { NextRequest } from "next/server";

import { proxyToBackendAuthed } from "@/lib/backendProxy";

/** Copilot LLM calls can exceed Vercel's default 60s proxy window. */
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  return proxyToBackendAuthed(request, "/api/v1/board-platform/copilot");
}
