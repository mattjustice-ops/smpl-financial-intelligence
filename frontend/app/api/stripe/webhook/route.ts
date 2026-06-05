import { NextResponse } from "next/server";

import { syncCheckoutToHubSpot } from "@/lib/billing/hubspot-checkout";
import { backendBaseUrl, callBillingBackend, getStripe, getStripeWebhookSecret } from "@/lib/billing/stripe-server";

export const runtime = "nodejs";

/** Browsers use GET — this is not an error; Stripe sends POST with a signed payload. */
export async function GET() {
  return NextResponse.json({
    ok: true,
    message:
      "Stripe webhook endpoint is active. Do not open this URL in the browser for testing. Add it in Stripe Dashboard → Developers → Webhooks (POST only).",
  });
}

const HANDLED_EVENTS = new Set([
  "checkout.session.completed",
  "customer.subscription.created",
  "customer.subscription.updated",
  "customer.subscription.deleted",
  "invoice.payment_succeeded",
  "invoice.payment_failed",
  "customer.updated",
]);

export async function POST(request: Request) {
  const webhookSecret = getStripeWebhookSecret();
  if (!webhookSecret) {
    return NextResponse.json(
      {
        error:
          "Stripe webhook secret is not configured. Set STRIPE_WEBHOOK_SECRET, add whsec_... to Stripe Token.txt, or run stripe listen.",
      },
      { status: 500 }
    );
  }

  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "Missing stripe-signature header." }, { status: 400 });
  }

  const rawBody = await request.text();
  const stripe = getStripe();

  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid signature";
    console.error("[stripe/webhook] signature verification failed:", message);
    return NextResponse.json({ error: message }, { status: 400 });
  }

  if (!HANDLED_EVENTS.has(event.type)) {
    return NextResponse.json({ received: true, skipped: true });
  }

  const backend = backendBaseUrl();
  if (!backend) {
    console.error("[stripe/webhook] SFI_BACKEND_URL not set — cannot persist billing state.");
    return NextResponse.json({ error: "Billing backend not configured." }, { status: 503 });
  }

  try {
    const processRes = await callBillingBackend("/api/v1/billing/stripe-events", {
      method: "POST",
      body: {
        stripe_event_id: event.id,
        event_type: event.type,
        payload: event as unknown as Record<string, unknown>,
      },
    });

    if (!processRes.ok) {
      const detail = await processRes.text();
      console.error("[stripe/webhook] backend process failed:", processRes.status, detail);
      return NextResponse.json({ error: "Failed to process event." }, { status: 500 });
    }

    const result = (await processRes.json()) as {
      ok?: boolean;
      duplicate?: boolean;
      organization_id?: string;
    };

    if (event.type === "checkout.session.completed" && !result.duplicate) {
      const session = event.data.object as {
        metadata?: Record<string, string>;
        customer?: string;
        subscription?: string;
      };
      const plan = session.metadata?.plan ?? "starter";
      const interval = session.metadata?.billing_interval ?? "contract";

      try {
        await syncCheckoutToHubSpot({
          hubspotDealId: session.metadata?.hubspot_deal_id,
          plan,
          billingInterval: interval,
          stripeCustomerId: String(session.customer),
          stripeSubscriptionId: session.subscription
            ? String(session.subscription)
            : undefined,
        });
      } catch (hubspotError) {
        console.error("[stripe/webhook] HubSpot sync skipped:", hubspotError);
      }
    }

    return NextResponse.json({
      received: true,
      duplicate: result.duplicate ?? false,
      organization_id: result.organization_id,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Webhook handler error";
    console.error("[stripe/webhook]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
