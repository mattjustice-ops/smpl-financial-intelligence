import { NextResponse } from "next/server";

import { syncRequestQuoteToHubSpot } from "@/lib/hubspot/sync";
import { scoreLead } from "@/lib/request-quote/scoring";
import { persistSubmission, updateSubmissionHubSpot } from "@/lib/request-quote/storage";
import type { RequestQuoteFormData, RequestQuotePayload, RequestQuoteResponse } from "@/lib/request-quote/types";
import { sanitizeForm, validateFullForm } from "@/lib/request-quote/validation";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid JSON body." }, { status: 400 });
  }

  const form = sanitizeForm(body as RequestQuoteFormData);
  const errors = validateFullForm(form);
  if (errors.length > 0) {
    return NextResponse.json({ ok: false, errors }, { status: 400 });
  }

  const scoring = scoreLead(form);
  const payload: RequestQuotePayload = {
    ...form,
    leadScore: scoring.score,
    leadTier: scoring.tier,
    recommendedPackage: scoring.recommendedPackage,
    estimatedDealAmount: scoring.estimatedDealAmount,
    scoringRationale: scoring.rationale,
    submittedAt: new Date().toISOString(),
  };

  const stored = await persistSubmission(payload, "pending");

  const hubspot = await syncRequestQuoteToHubSpot(payload);
  if (stored.storageMethod === "database") {
    await updateSubmissionHubSpot(stored.id, hubspot);
  }

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
}
