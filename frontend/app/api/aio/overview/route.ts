import { NextRequest, NextResponse } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { getOverview, seedAioConfig } from "@/lib/aio/db";

export async function GET() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const overview = await getOverview();
    return NextResponse.json(overview);
  } catch (error) {
    console.error("[aio/overview]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Failed to load overview" },
      { status: 500 },
    );
  }
}

/** POST seeds queries + competitors and returns overview */
export async function POST(_request: NextRequest) {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const seeded = await seedAioConfig();
    const overview = await getOverview();
    return NextResponse.json({ seeded, overview });
  } catch (error) {
    console.error("[aio/seed]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Seed failed" },
      { status: 500 },
    );
  }
}
