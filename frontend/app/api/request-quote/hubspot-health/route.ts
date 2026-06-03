import { NextResponse } from "next/server";

import { checkHubSpotHealth } from "@/lib/hubspot/client";

export const runtime = "nodejs";

export async function GET() {
  const health = await checkHubSpotHealth();
  return NextResponse.json(health, { status: health.tokenConfigured && health.pipelineFound ? 200 : 503 });
}
