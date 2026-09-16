import { NextResponse } from "next/server";

import { getPulseOverview } from "@/lib/aio/db";
import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";

export async function GET() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const pulse = await getPulseOverview();
    return NextResponse.json(pulse);
  } catch (error) {
    console.error("[aio/pulse]", error);
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Failed to load pulse",
      },
      { status: 500 },
    );
  }
}
