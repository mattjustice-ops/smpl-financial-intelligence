import { PRODUCT_MODULES } from "@/components/landing/constants";

export type PricingTierId = "starter" | "professional" | "enterprise";

/** @deprecated Use PricingTierId. Kept for Stripe webhook/checkout APIs. */
export type BillingPlan = "starter" | "professional";
export type BillingInterval = "monthly" | "annual";

export const BILLING_PLANS = ["starter", "professional"] as const;
export const BILLING_INTERVALS = ["monthly", "annual"] as const;

export type SupportLevel = "Silver Support" | "Gold Support" | "Platinum Support";

export type PricingTier = {
  id: PricingTierId;
  name: string;
  support: SupportLevel;
  usersIncluded: number;
  integrationsIncluded: number;
  highlights: string[];
  /** Full platform module list (Enterprise). */
  moduleNames?: readonly string[];
  /** Sales-led: pricing and contract terms are finalized after demo. */
  pricingNote: string;
};

const ALL_MODULE_NAMES = PRODUCT_MODULES.map((m) => m.title);

export const PRICING_TIERS: Record<PricingTierId, PricingTier> = {
  starter: {
    id: "starter",
    name: "Starter",
    support: "Silver Support",
    usersIncluded: 2,
    integrationsIncluded: 1,
    pricingNote: "Pricing and billing terms are tailored after your demo.",
    highlights: [
      "Dedicated environment",
      "Dashboards",
      "Board reporting",
      "AI commentary",
      "CSV uploads",
      "1 integration included",
      "2 users included",
    ],
  },
  professional: {
    id: "professional",
    name: "Professional",
    support: "Gold Support",
    usersIncluded: 5,
    integrationsIncluded: 3,
    pricingNote: "Pricing and billing terms are tailored after your demo.",
    highlights: [
      "Dedicated environment",
      "Dashboards",
      "Board reporting",
      "Forecasting",
      "Workforce planning",
      "Scenario analysis",
      "AI commentary",
      "3 integrations included",
      "5 users included",
    ],
  },
  enterprise: {
    id: "enterprise",
    name: "Enterprise",
    support: "Platinum Support",
    usersIncluded: 10,
    integrationsIncluded: 5,
    pricingNote: "Custom packaging, contracting, and onboarding.",
    highlights: [
      "Dedicated environment",
      "Dashboards",
      "AI commentary",
      "5 integrations included",
      "10 users included",
      "SSO and advanced security",
      "White-glove onboarding",
    ],
    moduleNames: ALL_MODULE_NAMES,
  },
};

/** @deprecated Public pricing no longer displays amounts. */
export const PLAN_CATALOG = {
  starter: {
    id: "starter" as const,
    name: "Starter",
    monthlyPrice: 0,
    annualPrice: 0,
    usersIncluded: PRICING_TIERS.starter.usersIncluded,
    features: PRICING_TIERS.starter.highlights,
  },
  professional: {
    id: "professional" as const,
    name: "Professional",
    monthlyPrice: 0,
    annualPrice: 0,
    usersIncluded: PRICING_TIERS.professional.usersIncluded,
    features: PRICING_TIERS.professional.highlights,
  },
};

export const PRICING_TIER_ORDER: PricingTierId[] = ["starter", "professional", "enterprise"];

export function requestQuoteHref(tier: PricingTierId): string {
  return `/request-quote?plan=${encodeURIComponent(tier)}`;
}

export function bookDemoHref(tier: PricingTierId): string {
  return `/book-demo?plan=${encodeURIComponent(tier)}`;
}
