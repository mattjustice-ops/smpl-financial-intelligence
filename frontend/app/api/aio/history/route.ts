import { NextResponse } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { getVisibilityHistory } from "@/lib/aio/db";

export async function GET() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    return NextResponse.json(await getVisibilityHistory());
  } catch (error) {
    console.error("[aio/history]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Failed to load visibility history" },
      { status: 500 },
    );
  }
}
