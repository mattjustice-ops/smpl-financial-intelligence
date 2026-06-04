import { NextResponse } from "next/server";

import { syncRequestQuoteToHubSpot } from "@/lib/hubspot/sync";
import { scoreLead } from "@/lib/request-quote/scoring";
import { persistSubmission, updateSubmissionHubSpot } from "@/lib/request-quote/storage";
import type {
  HubSpotSyncResult,
  RequestQuoteFormData,
  RequestQuotePayload,
  RequestQuoteResponse,
} from "@/lib/request-quote/types";
import { buildQuotePayload, sanitizeForm, validateForm } from "@/lib/request-quote/validation";

export const runtime = "nodejs";

async function finishHubSpotSync(
  stored: { id: string; storageMethod: "database" | "log" },
  payload: RequestQuotePayload
): Promise<HubSpotSyncResult> {
  const hubspot = await syncRequestQuoteToHubSpot(payload);
  if (stored.storageMethod === "database") {
    await updateSubmissionHubSpot(stored.id, hubspot);
  }
  return hubspot;
}

export async function POST(request: Request) {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json({ ok: false, error: "Invalid JSON body." }, { status: 400 });
    }

    const raw = body as RequestQuoteFormData;
    const form = sanitizeForm({
      ...raw,
      submissionIntent: raw.submissionIntent === "demo" ? "demo" : "quote",
    });
    const errors = validateForm(form);
    if (errors.length > 0) {
      return NextResponse.json({ ok: false, errors }, { status: 400 });
    }

    const scoring = scoreLead(form);
    const payload = buildQuotePayload(form, scoring);

    const stored = await persistSubmission(payload, "pending");

    // Demo and quote use the same HubSpot path (contact, company, deal, associations).
    const hubspot = await finishHubSpotSync(stored, payload);

    const response: RequestQuoteResponse = {
      ok: true,
      submissionId: stored.id,
      leadScore: scoring.score,
      leadTier: scoring.tier,
      recommendedPackage: scoring.recommendedPackage,
      estimatedDealAmount: scoring.estimatedDealAmount,
      stored: stored.storageMethod === "database",
      storageMethod: stored.storageMethod,
      hubspot,
    };

    return NextResponse.json(response, { status: 200 });
  } catch (error) {
    console.error("[request-quote] submission failed:", error);
    return NextResponse.json(
      { ok: false, error: "We could not save your request. Please try again." },
      { status: 500 }
    );
  }
}
