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

export function backendBaseUrl(): string | null {
  return (
    process.env.SFI_BACKEND_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    null
  );
}

type BillingBackendInit = Omit<RequestInit, "body"> & {
  body?: Record<string, unknown>;
};

export async function callBillingBackend(
  path: string,
  init: BillingBackendInit = {}
): Promise<Response> {
  const base = backendBaseUrl();
  if (!base) {
    throw new Error("SFI_BACKEND_URL is not configured.");
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  const internalKey = process.env.BILLING_INTERNAL_API_KEY?.trim();
  if (internalKey) {
    headers["X-Billing-Internal-Key"] = internalKey;
  }

  return fetch(`${base.replace(/\/$/, "")}${path}`, {
    ...init,
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
}
