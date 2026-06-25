import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/backendProxy";

/** Runtime config for static board iframe (avoids baking secrets into public HTML). */
export async function GET() {
  const longRunningApiBase = backendUrl().replace(/\/$/, "");
  return NextResponse.json(
    {
      longRunningApiBase,
      useDirectRailway: Boolean(longRunningApiBase && !/localhost|127\.0\.0\.1/i.test(longRunningApiBase)),
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
