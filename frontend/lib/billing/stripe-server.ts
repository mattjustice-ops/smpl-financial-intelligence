import "server-only";

import Stripe from "stripe";

import type { BillingInterval, BillingPlan } from "./plans";
import { getStripeSecretKey } from "./stripe-secrets";

export function getStripe(): Stripe {
  const key = getStripeSecretKey();
  if (!key) {
    throw new Error(
      "Stripe secret key is not configured. Set STRIPE_SECRET_KEY or STRIPE_TOKEN_FILE (see Stripe Token.txt)."
    );
  }
  return new Stripe(key);
}

export { getStripePublishableKey, getStripeSecretKey, getStripeWebhookSecret } from "./stripe-secrets";
export { backendBaseUrl, callBillingBackend } from "./backend-client";

export function getAppBaseUrl(): string {
  return (
    process.env.APP_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_APP_URL?.trim() ||
    "http://localhost:3000"
  ).replace(/\/$/, "");
}

export function resolvePriceId(plan: BillingPlan, interval: BillingInterval): string {
  const map: Record<BillingPlan, Record<BillingInterval, string | undefined>> = {
    starter: {
      monthly: process.env.STRIPE_STARTER_MONTHLY_PRICE_ID,
      annual: process.env.STRIPE_STARTER_ANNUAL_PRICE_ID,
    },
    professional: {
      monthly:
        process.env.STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID ??
        process.env.STRIPE_GROWTH_MONTHLY_PRICE_ID,
      annual:
        process.env.STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID ??
        process.env.STRIPE_GROWTH_ANNUAL_PRICE_ID,
    },
  };

  const priceId = map[plan][interval]?.trim();
  if (!priceId) {
    throw new Error(`Stripe price ID not configured for ${plan} ${interval}.`);
  }
  return priceId;
}

export function resolveImplementationPriceId(plan: BillingPlan): string | undefined {
  const map: Record<BillingPlan, string | undefined> = {
    starter: process.env.STRIPE_STARTER_IMPLEMENTATION_PRICE_ID,
    professional:
      process.env.STRIPE_PROFESSIONAL_IMPLEMENTATION_PRICE_ID ??
      process.env.STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID,
  };
  return map[plan]?.trim();
}
