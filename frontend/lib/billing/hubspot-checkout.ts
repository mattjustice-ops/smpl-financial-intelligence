import { getHubSpotToken, HubSpotClient } from "../hubspot/client";

export async function syncCheckoutToHubSpot(params: {
  hubspotDealId?: string;
  plan: string;
  billingInterval: string;
  stripeCustomerId: string;
  stripeSubscriptionId?: string;
  annualContractValue?: number;
}): Promise<void> {
  const token = getHubSpotToken();
  if (!token || !params.hubspotDealId) {
    return;
  }

  const client = new HubSpotClient(token);
  const amount =
    params.annualContractValue !== undefined ? String(params.annualContractValue) : undefined;

  const closedWonStage = process.env.HUBSPOT_DEAL_STAGE_CLOSED_WON?.trim();

  await client.updateDeal(params.hubspotDealId, {
    ...(amount ? { amount } : {}),
    ...(closedWonStage ? { dealstage: closedWonStage } : {}),
    description: [
      `Customer completed Stripe checkout for ${params.plan} (${params.billingInterval}).`,
      `Stripe customer: ${params.stripeCustomerId}`,
      params.stripeSubscriptionId ? `Stripe subscription: ${params.stripeSubscriptionId}` : "",
    ]
      .filter(Boolean)
      .join("\n"),
  });
}
