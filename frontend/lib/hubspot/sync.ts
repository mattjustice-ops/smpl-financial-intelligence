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

function companyCoreProperties(payload: RequestQuotePayload): Record<string, string> {
  return {
    ...companyIdentityProperties(payload),
    description: formatCompanyDescription(payload),
    about_us: formatCompanyDescription(payload),
  };
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
    const companyProps = companyCoreProperties(payload);
    const companyId = await client.upsertCompany(companyProps);

    const companyTextUpdate = await client.updateCompanyResilient(companyId, {
      description: companyProps.description,
      about_us: companyProps.about_us,
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

    try {
      await client.associateContactToCompany(contactId, companyId);
      await client.associateDeal(dealId, "contacts", contactId);
      await client.associateDeal(dealId, "companies", companyId);
    } catch (associationError) {
      warnings.push(
        `Records were created but associations failed: ${formatHubSpotError(associationError)}`
      );
    }

    return {
      ok: true,
      contactId,
      companyId,
      dealId,
      warnings: warnings.length ? warnings : undefined,
    };
  } catch (error) {
    const message = formatHubSpotError(error);
    console.error("[request-quote] HubSpot sync failed:", message);
    return { ok: false, error: message };
  }
}
