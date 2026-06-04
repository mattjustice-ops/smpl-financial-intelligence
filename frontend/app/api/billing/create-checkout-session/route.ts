import { NextResponse } from "next/server";

import { PLAN_CATALOG } from "@/lib/billing/plans";
import {
  backendBaseUrl,
  callBillingBackend,
  getAppBaseUrl,
  getStripe,
  resolveImplementationPriceId,
  resolvePriceId,
} from "@/lib/billing/stripe-server";
import { parseCreateCheckoutInput } from "@/lib/billing/validation";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const input = parseCreateCheckoutInput(await request.json());
    const stripe = getStripe();
    const baseUrl = getAppBaseUrl();

    const backend = backendBaseUrl();
    if (backend) {
      const rateRes = await fetch(
        `${backend.replace(/\/$/, "")}/api/v1/billing/checkout-rate-limit?email=${encodeURIComponent(input.customer_email)}`,
        { cache: "no-store" }
      );
      if (rateRes.ok) {
        const rate = (await rateRes.json()) as { allowed?: boolean };
        if (rate.allowed === false) {
          return NextResponse.json(
            { ok: false, error: "Too many checkout attempts. Try again later." },
            { status: 429 }
          );
        }
      }
    }

    const subscriptionPriceId = resolvePriceId(
      input.plan as "starter" | "professional",
      input.billing_interval as "monthly" | "annual"
    );

    const lineItems: Array<{ price: string; quantity: number }> = [
      { price: subscriptionPriceId, quantity: 1 },
    ];

    if (input.include_implementation_fee) {
      const implPriceId = resolveImplementationPriceId(input.plan as "starter" | "professional");
      if (implPriceId) {
        lineItems.push({ price: implPriceId, quantity: 1 });
      }
    }

    const existingCustomers = await stripe.customers.list({
      email: input.customer_email,
      limit: 1,
    });
    const existingCustomerId = existingCustomers.data[0]?.id;

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: existingCustomerId,
      customer_email: existingCustomerId ? undefined : input.customer_email,
      line_items: lineItems,
      allow_promotion_codes: true,
      success_url: `${baseUrl}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/pricing?checkout=cancelled`,
      metadata: {
        plan: input.plan,
        billing_interval: input.billing_interval,
        company_name: input.company_name,
        customer_email: input.customer_email,
        hubspot_contact_id: input.hubspot_contact_id ?? "",
        hubspot_company_id: input.hubspot_company_id ?? "",
        hubspot_deal_id: input.hubspot_deal_id ?? "",
      },
      subscription_data: {
        metadata: {
          plan: input.plan,
          billing_interval: input.billing_interval,
          company_name: input.company_name,
        },
      },
    });

    if (!session.url) {
      return NextResponse.json({ ok: false, error: "Stripe did not return a checkout URL." }, { status: 500 });
    }

    if (backend) {
      try {
        await callBillingBackend("/api/v1/billing/checkout-sessions", {
          method: "POST",
          body: {
            stripe_checkout_session_id: session.id,
            customer_email: input.customer_email,
            plan: input.plan,
            billing_interval: input.billing_interval,
          },
        });
      } catch (error) {
        console.error("[billing] failed to record checkout session:", error);
      }
    }

    const planInfo = PLAN_CATALOG[input.plan as keyof typeof PLAN_CATALOG];
    return NextResponse.json({
      ok: true,
      url: session.url,
      sessionId: session.id,
      plan: planInfo.name,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Checkout failed.";
    console.error("[billing] create-checkout-session:", message);
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
