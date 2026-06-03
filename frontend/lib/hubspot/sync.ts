import { cleanProperties, getHubSpotToken, HubSpotClient } from "./client";
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

function companyProperties(payload: RequestQuotePayload): Record<string, string> {
  return cleanProperties({
    name: payload.companyName,
    domain: payload.domain,
    industry: payload.industry,
    smpl_arr_range: payload.arrRange,
    smpl_employee_count: payload.employeeCount,
    smpl_finance_team_size: payload.financeTeamSize,
    smpl_company_stage: payload.companyStage,
    smpl_current_erp: payload.currentErp,
    smpl_current_crm: payload.currentCrm,
    smpl_current_billing_system: payload.currentBilling,
    smpl_current_hris: payload.currentHris,
    smpl_current_planning_tool: payload.currentPlanning,
    smpl_data_reliability: payload.dataReliability,
  });
}

function dealProperties(
  payload: RequestQuotePayload,
  pipelineId: string,
  dealstage: string
): Record<string, string> {
  return cleanProperties({
    dealname: `${payload.companyName} — SMPL Quote Request`,
    pipeline: pipelineId,
    dealstage,
    amount: String(payload.estimatedDealAmount),
    smpl_requested_modules: payload.requestedModules.join("; "),
    smpl_business_needs: payload.businessNeeds,
    smpl_biggest_challenge: payload.biggestChallenge,
    smpl_current_solution: payload.currentSolution || undefined,
    smpl_expected_users: payload.expectedUsers,
    smpl_implementation_timeline: payload.implementationTimeline,
    smpl_deployment_preference: payload.deploymentPreference,
    smpl_budget_range: payload.budgetRange,
    smpl_lead_score: String(payload.leadScore),
    smpl_recommended_package: payload.recommendedPackage,
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

  try {
    const contactId = await client.upsertContact(contactProperties(payload));
    const companyId = await client.upsertCompany(companyProperties(payload));
    const { pipelineId, dealstage } = await client.resolvePipeline();
    const dealId = await client.createDeal(dealProperties(payload, pipelineId, dealstage));

    await client.associateDefault("contacts", contactId, "companies", companyId);
    await client.associateDefault("deals", dealId, "contacts", contactId);
    await client.associateDefault("deals", dealId, "companies", companyId);

    return { ok: true, contactId, companyId, dealId };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown HubSpot error";
    console.error("[request-quote] HubSpot sync failed:", message);
    return { ok: false, error: message };
  }
}
