import { NextResponse } from "next/server";

/**
 * Runtime config for the static board iframe. The browser never calls Railway directly:
 * every API call goes through the same-origin /api/v1 proxy, so the base is always empty.
 */
export async function GET() {
  return NextResponse.json(
    {
      longRunningApiBase: "",
      useDirectRailway: false,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
