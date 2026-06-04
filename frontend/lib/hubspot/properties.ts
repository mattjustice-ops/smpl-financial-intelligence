import type { RequestQuotePayload } from "../request-quote/types";

export const CONTACT_STANDARD_KEYS = ["firstname", "lastname", "email", "jobtitle", "phone"] as const;

export const COMPANY_STANDARD_KEYS = ["name", "domain"] as const;

export const DEAL_STANDARD_KEYS = ["dealname", "pipeline", "dealstage", "amount", "description"] as const;

export function pickProperties(
  all: Record<string, string>,
  keys: readonly string[]
): Record<string, string> {
  return Object.fromEntries(keys.filter((key) => all[key]).map((key) => [key, all[key]!]));
}

export function companyIdentityProperties(payload: RequestQuotePayload): Record<string, string> {
  const domain = payload.domain.replace(/^www\./, "");

  return cleanProperties({
    name: payload.companyName.trim(),
    domain,
    website: domain ? `https://${domain}` : undefined,
  });
}

function cleanProperties(properties: Record<string, string | undefined>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined && value !== "")
  ) as Record<string, string>;
}

function submissionLabel(payload: RequestQuotePayload): "Demo" | "Quote" {
  return payload.submissionIntent === "demo" ? "Demo" : "Quote";
}

export function formatCompanyDescription(payload: RequestQuotePayload): string {
  return [
    `SMPL ${submissionLabel(payload)} Request`,
    `Company: ${payload.companyName}`,
    `Contact: ${payload.firstname} ${payload.lastname} (${payload.email})`,
    `Job title: ${payload.jobtitle}`,
    payload.phone ? `Phone: ${payload.phone}` : "",
    `Location: ${payload.state}, ${payload.country}`,
    `Data reliability: ${payload.dataReliability}`,
    `Primary needs / issues: ${payload.primaryNeeds}`,
    `Recommended package: ${payload.recommendedPackage}`,
    payload.preferredPlan ? `Interested plan: ${payload.preferredPlan}` : "",
    `Submitted: ${payload.submittedAt}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function formatDealDescription(payload: RequestQuotePayload): string {
  return [
    `SMPL ${submissionLabel(payload)} — Deal summary`,
    `Recommended package: ${payload.recommendedPackage}`,
    `Lead score: ${payload.leadScore}`,
    `Primary needs / issues: ${payload.primaryNeeds}`,
    `Data reliability: ${payload.dataReliability}`,
    `Location: ${payload.state}, ${payload.country}`,
    payload.preferredPlan ? `Pricing tier selected: ${payload.preferredPlan}` : "",
    `Submitted: ${payload.submittedAt}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function companyExtendedProperties(payload: RequestQuotePayload): Record<string, string> {
  return {
    smpl_industry: payload.industry,
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
  };
}

export function dealExtendedProperties(payload: RequestQuotePayload): Record<string, string> {
  return {
    smpl_requested_modules: payload.requestedModules.join("; "),
    smpl_business_needs: payload.businessNeeds,
    smpl_biggest_challenge: payload.biggestChallenge,
    smpl_current_solution: payload.currentSolution || "",
    smpl_expected_users: payload.expectedUsers,
    smpl_implementation_timeline: payload.implementationTimeline,
    smpl_deployment_preference: payload.deploymentPreference,
    smpl_budget_range: payload.budgetRange,
    smpl_lead_score: String(payload.leadScore),
    smpl_recommended_package: payload.recommendedPackage,
  };
}

export function formatHubSpotError(error: unknown): string {
  if (!(error instanceof Error)) return "Unknown HubSpot error";
  return error.message;
}
