import { NextResponse } from "next/server";

import { canAccessOrganization, requireAuthenticatedSession } from "@/lib/auth/server-org-access";
import {
  backendBaseUrl,
  callBillingBackend,
  getAppBaseUrl,
  getStripe,
} from "@/lib/billing/stripe-server";

export const runtime = "nodejs";

/**
 * A portal session can change payment methods and cancel subscriptions, so the Stripe
 * customer is always resolved server-side from an organization the signed-in user belongs to.
 */
export async function POST(request: Request) {
  try {
    const authResult = await requireAuthenticatedSession();
    if ("error" in authResult) {
      return authResult.error;
    }

    const body = (await request.json()) as { organization_id?: string };
    const organizationId = body.organization_id?.trim();
    if (!organizationId) {
      return NextResponse.json({ ok: false, error: "organization_id is required." }, { status: 400 });
    }
    if (!canAccessOrganization(authResult.session, organizationId)) {
      return NextResponse.json(
        { ok: false, error: "You do not have access to this organization." },
        { status: 403 }
      );
    }

    if (!backendBaseUrl()) {
      return NextResponse.json(
        { ok: false, error: "Billing backend is not configured." },
        { status: 503 }
      );
    }

    const params = new URLSearchParams({ organization_id: organizationId });
    const accountRes = await callBillingBackend(`/api/v1/billing/account?${params.toString()}`);
    if (!accountRes.ok) {
      return NextResponse.json({ ok: false, error: "Billing account not found." }, { status: 404 });
    }
    const account = (await accountRes.json()) as { stripe_customer_id?: string };
    const stripeCustomerId = account.stripe_customer_id;

    if (!stripeCustomerId) {
      return NextResponse.json(
        { ok: false, error: "No Stripe customer on file for this account." },
        { status: 404 }
      );
    }

    const stripe = getStripe();
    const portal = await stripe.billingPortal.sessions.create({
      customer: stripeCustomerId,
      return_url: `${getAppBaseUrl()}/account/billing`,
    });

    return NextResponse.json({ ok: true, url: portal.url });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Portal session failed.";
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
