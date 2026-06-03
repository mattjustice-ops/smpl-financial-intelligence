import { cleanProperties, getHubSpotToken, HubSpotClient } from "./client";
import {
  companyExtendedProperties,
  companyIdentityProperties,
  dealExtendedProperties,
  formatCompanyDescription,
  formatDealDescription,
  formatHubSpotError,
} from "./properties";
import type { HubSpotSyncResult, RequestQuotePayload } from "../request-quote/types";

function contactProperties(payload: RequestQuotePayload): Record<string, string> {
  return cleanProperties({
    firstname: payload.firstname,
    lastname: payload.lastname,
    email: payload.email,
    jobtitle: payload.jobtitle,
    phone: payload.phone || undefined,
  });
}

function dealCoreProperties(
  payload: RequestQuotePayload,
  pipelineId: string,
  dealstage: string
): Record<string, string> {
  return cleanProperties({
    dealname: `${payload.companyName} — SMPL Quote Request`,
    pipeline: pipelineId,
    dealstage,
    amount: String(payload.estimatedDealAmount),
    description: formatDealDescription(payload),
  });
}

export async function syncRequestQuoteToHubSpot(
  payload: RequestQuotePayload
): Promise<HubSpotSyncResult> {
  const token = getHubSpotToken();
  if (!token) {
    return { ok: false, error: "HubSpot token is not configured on the server." };
  }

  const client = new HubSpotClient(token);
  const warnings: string[] = [];

  try {
    const contactId = await client.upsertContact(contactProperties(payload));
    const companySync = await client.syncCompanyRecord(
      companyIdentityProperties(payload),
      payload.industry
    );
    const companyId = companySync.companyId;

    if (companySync.skipped.length > 0) {
      for (const item of companySync.skipped) {
        warnings.push(`${item.property}: ${item.reason}`);
      }
    }

    const companyTextUpdate = await client.updateCompanyResilient(companyId, {
      description: formatCompanyDescription(payload),
      about_us: formatCompanyDescription(payload),
    });
    if (companyTextUpdate.skipped.length > 0) {
      warnings.push(
        `Some company narrative fields were skipped (${companyTextUpdate.skipped.length}). Check Description/About on the company record.`
      );
    }

    const { pipelineId, dealstage } = await client.resolvePipeline();
    const dealId = await client.createDeal(dealCoreProperties(payload, pipelineId, dealstage));

    const companyExtended = await client.patchExtendedProperties(
      "companies",
      companyId,
      companyExtendedProperties(payload)
    );
    if (companyExtended.skipped.length > 0) {
      warnings.push(
        `Company custom fields skipped (${companyExtended.skipped.length}). Details are in the company description.`
      );
    }

    const dealExtended = await client.patchExtendedProperties("deals", dealId, dealExtendedProperties(payload));
    if (dealExtended.skipped.length > 0) {
      warnings.push(
        `Deal custom fields skipped (${dealExtended.skipped.length}). Details are in the deal description.`
      );
    }

    let associationDebug:
      | {
          applied: string[];
          verifiedContactCompanies: string[];
          verifiedCompanyContacts: string[];
        }
      | undefined;

    try {
      associationDebug = await client.linkQuoteRecords(contactId, companyId, dealId);
    } catch (associationError) {
      warnings.push(`Association failed: ${formatHubSpotError(associationError)}`);
      associationDebug = {
        applied: [],
        verifiedContactCompanies: [],
        verifiedCompanyContacts: [],
      };
    }

    const companyOk = Boolean(companySync.verified.name);

    return {
      ok: companyOk && Boolean(associationDebug?.verifiedContactCompanies.map(String).includes(String(companyId))),
      contactId,
      companyId,
      dealId,
      error: companyOk
        ? associationDebug?.verifiedContactCompanies.map(String).includes(String(companyId))
          ? undefined
          : "HubSpot records were created but the contact and company were not linked."
        : "HubSpot company record was found/created but company name did not save. See companyDebug for details.",
      warnings: warnings.length ? warnings : undefined,
      associationDebug,
      companyDebug: {
        applied: companySync.applied,
        skipped: companySync.skipped,
        verified: companySync.verified,
      },
    };
  } catch (error) {
    const message = formatHubSpotError(error);
    console.error("[request-quote] HubSpot sync failed:", message);
    return { ok: false, error: message };
  }
}
