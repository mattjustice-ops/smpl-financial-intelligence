import { NextResponse } from "next/server";

import { backendBaseUrl, getAppBaseUrl, getStripe } from "@/lib/billing/stripe-server";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      organization_id?: string;
      stripe_customer_id?: string;
      email?: string;
    };

    let stripeCustomerId = body.stripe_customer_id?.trim();

    if (!stripeCustomerId) {
      const backend = backendBaseUrl();
      if (!backend) {
        return NextResponse.json(
          { ok: false, error: "Billing backend is not configured." },
          { status: 503 }
        );
      }

      const params = new URLSearchParams();
      if (body.organization_id) {
        params.set("organization_id", body.organization_id);
      } else if (body.email) {
        params.set("email", body.email);
      } else {
        return NextResponse.json(
          { ok: false, error: "organization_id, stripe_customer_id, or email is required." },
          { status: 400 }
        );
      }

      const accountRes = await fetch(
        `${backend.replace(/\/$/, "")}/api/v1/billing/account?${params.toString()}`,
        { cache: "no-store" }
      );
      if (!accountRes.ok) {
        return NextResponse.json({ ok: false, error: "Billing account not found." }, { status: 404 });
      }
      const account = (await accountRes.json()) as { stripe_customer_id?: string };
      stripeCustomerId = account.stripe_customer_id;
    }

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
