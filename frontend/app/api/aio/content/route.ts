import { NextResponse } from "next/server";

import { listAioContent, seedAioContent } from "@/lib/aio/db";
import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";

export async function GET() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const content = await listAioContent();
    return NextResponse.json({ content, count: content.length });
  } catch (error) {
    console.error("[aio/content]", error);
    return NextResponse.json(
      {
        detail:
          error instanceof Error ? error.message : "Failed to load content",
      },
      { status: 500 },
    );
  }
}

/** POST re-seeds content registry + page→query maps from seed_content.json */
export async function POST() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const seeded = await seedAioContent();
    const content = await listAioContent();
    return NextResponse.json({ seeded, content });
  } catch (error) {
    console.error("[aio/content seed]", error);
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Content seed failed",
      },
      { status: 500 },
    );
  }
}
