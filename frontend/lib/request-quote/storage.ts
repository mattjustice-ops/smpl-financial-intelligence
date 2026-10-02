import { backendBaseUrl, callBillingBackend } from "@/lib/billing/backend-client";

import type { HubSpotSyncResult, RequestQuotePayload } from "./types";

type StoredSubmission = {
  id: string;
  storageMethod: "database" | "log";
};

export async function persistSubmission(
  payload: RequestQuotePayload,
  hubspotStatus: "pending" | "success" | "failed" = "pending",
  hubspotError?: string | null
): Promise<StoredSubmission> {
  if (backendBaseUrl()) {
    try {
      const res = await callBillingBackend("/api/v1/quotes/submit", {
        method: "POST",
        body: {
          email: payload.email,
          payload,
          lead_score: payload.leadScore,
          recommended_package: payload.recommendedPackage,
          hubspot_sync_status: hubspotStatus,
          hubspot_error: hubspotError ?? null,
        },
      });

      if (res.ok) {
        const data = (await res.json()) as { id: string };
        return { id: data.id, storageMethod: "database" };
      }

      const detail = await res.text();
      console.error("[request-quote] backend storage failed:", res.status, detail);
    } catch (error) {
      console.error("[request-quote] backend storage error:", error);
    }
  }

  console.log("[request-quote] submission payload:", JSON.stringify(payload, null, 2));
  return { id: crypto.randomUUID(), storageMethod: "log" };
}

export async function updateSubmissionHubSpot(
  submissionId: string,
  hubspot: HubSpotSyncResult
): Promise<void> {
  if (!backendBaseUrl() || hubspot.ok === undefined) return;

  try {
    await callBillingBackend(`/api/v1/quotes/submit/${submissionId}`, {
      method: "PATCH",
      body: {
        hubspot_contact_id: hubspot.contactId ?? null,
        hubspot_company_id: hubspot.companyId ?? null,
        hubspot_deal_id: hubspot.dealId ?? null,
        hubspot_sync_status: hubspot.ok ? "success" : "failed",
        hubspot_error: hubspot.error ?? null,
      },
    });
  } catch (error) {
    console.error("[request-quote] failed to update HubSpot ids:", error);
  }
}
