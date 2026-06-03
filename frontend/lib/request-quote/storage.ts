import type { HubSpotSyncResult, RequestQuotePayload } from "./types";

type StoredSubmission = {
  id: string;
  storageMethod: "database" | "log";
};

function backendBaseUrl(): string | null {
  return (
    process.env.SFI_BACKEND_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    null
  );
}

export async function persistSubmission(
  payload: RequestQuotePayload,
  hubspotStatus: "pending" | "success" | "failed" = "pending",
  hubspotError?: string | null
): Promise<StoredSubmission> {
  const backend = backendBaseUrl();
  if (backend) {
    try {
      const res = await fetch(`${backend.replace(/\/$/, "")}/api/v1/quotes/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: payload.email,
          payload,
          lead_score: payload.leadScore,
          recommended_package: payload.recommendedPackage,
          hubspot_sync_status: hubspotStatus,
          hubspot_error: hubspotError ?? null,
        }),
        cache: "no-store",
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
  const backend = backendBaseUrl();
  if (!backend || hubspot.ok === undefined) return;

  try {
    await fetch(`${backend.replace(/\/$/, "")}/api/v1/quotes/submit/${submissionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hubspot_contact_id: hubspot.contactId ?? null,
        hubspot_company_id: hubspot.companyId ?? null,
        hubspot_deal_id: hubspot.dealId ?? null,
        hubspot_sync_status: hubspot.ok ? "success" : "failed",
        hubspot_error: hubspot.error ?? null,
      }),
      cache: "no-store",
    });
  } catch (error) {
    console.error("[request-quote] failed to update HubSpot ids:", error);
  }
}
