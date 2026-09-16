import { NextRequest, NextResponse } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { listQueries } from "@/lib/aio/db";

export async function GET(request: NextRequest) {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const priorityMin = Number(
      request.nextUrl.searchParams.get("priorityMin") || "0",
    );
    const queries = await listQueries({
      priorityMin: Number.isFinite(priorityMin) ? priorityMin : 0,
      activeOnly: true,
    });
    return NextResponse.json({ queries });
  } catch (error) {
    console.error("[aio/queries]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Failed to list queries" },
      { status: 500 },
    );
  }
}
