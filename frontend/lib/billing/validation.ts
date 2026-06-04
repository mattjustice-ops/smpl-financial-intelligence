import { BILLING_INTERVALS, BILLING_PLANS, type BillingInterval, type BillingPlan } from "./plans";

export type CreateCheckoutInput = {
  plan: string;
  billing_interval: string;
  include_implementation_fee: boolean;
  customer_email: string;
  company_name: string;
  hubspot_contact_id?: string;
  hubspot_company_id?: string;
  hubspot_deal_id?: string;
};

export function parseCreateCheckoutInput(body: unknown): CreateCheckoutInput {
  if (!body || typeof body !== "object") {
    throw new Error("Invalid request body.");
  }

  const data = body as Record<string, unknown>;
  const plan = String(data.plan ?? "").toLowerCase();
  const billing_interval = String(data.billing_interval ?? "").toLowerCase();

  const normalizedPlan = plan === "growth" ? "professional" : plan;
  if (!BILLING_PLANS.includes(normalizedPlan as BillingPlan)) {
    throw new Error("plan must be starter or professional.");
  }
  if (!BILLING_INTERVALS.includes(billing_interval as BillingInterval)) {
    throw new Error("billing_interval must be monthly or annual.");
  }

  const customer_email = String(data.customer_email ?? "").trim().toLowerCase();
  const company_name = String(data.company_name ?? "").trim();
  if (!customer_email || !customer_email.includes("@")) {
    throw new Error("customer_email is required.");
  }
  if (!company_name) {
    throw new Error("company_name is required.");
  }

  return {
    plan: normalizedPlan,
    billing_interval,
    include_implementation_fee: Boolean(data.include_implementation_fee),
    customer_email,
    company_name,
    hubspot_contact_id: data.hubspot_contact_id
      ? String(data.hubspot_contact_id)
      : undefined,
    hubspot_company_id: data.hubspot_company_id
      ? String(data.hubspot_company_id)
      : undefined,
    hubspot_deal_id: data.hubspot_deal_id ? String(data.hubspot_deal_id) : undefined,
  };
}
