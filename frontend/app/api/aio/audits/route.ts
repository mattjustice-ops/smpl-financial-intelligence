import { NextRequest, NextResponse } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { createManualAudit, listManualAudits } from "@/lib/aio/db";

export async function GET() {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const audits = await listManualAudits(100);
    return NextResponse.json({ audits });
  } catch (error) {
    console.error("[aio/audits GET]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Failed to list audits" },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) return access.error;
  try {
    const body = await request.json();
    const queryText = String(body.queryText || "").trim();
    const rawResponse = String(body.rawResponse || "").trim();
    if (!queryText || !rawResponse) {
      return NextResponse.json(
        { detail: "queryText and rawResponse are required" },
        { status: 400 },
      );
    }
    const citationUrls = Array.isArray(body.citationUrls)
      ? body.citationUrls.map(String).filter(Boolean)
      : String(body.citationsText || "")
          .split(/[\n,\s]+/)
          .map((s: string) => s.trim())
          .filter((s: string) => /^https?:\/\//i.test(s));

    const audit = await createManualAudit({
      queryId: body.queryId || null,
      queryText,
      rawResponse,
      citationUrls,
      productNote: body.productNote || "ChatGPT Search (consumer)",
      notes: body.notes || "",
      cleanSessionConfirmed: Boolean(body.cleanSessionConfirmed),
      observedAt: body.observedAt || undefined,
      batchName: body.batchName || undefined,
      createdBy: access.session.user?.email || null,
    });
    return NextResponse.json({ audit });
  } catch (error) {
    console.error("[aio/audits POST]", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Failed to save audit" },
      { status: 500 },
    );
  }
}
