import { NextResponse } from "next/server";

import { getStripe } from "@/lib/billing/stripe-server";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const sessionId = new URL(request.url).searchParams.get("session_id");
  if (!sessionId) {
    return NextResponse.json({ ok: false, error: "session_id is required." }, { status: 400 });
  }

  try {
    const stripe = getStripe();
    const session = await stripe.checkout.sessions.retrieve(sessionId, {
      expand: ["subscription", "customer"],
    });

    return NextResponse.json({
      ok: true,
      status: session.status,
      payment_status: session.payment_status,
      customer_email: session.customer_details?.email ?? session.metadata?.customer_email,
      plan: session.metadata?.plan,
      billing_interval: session.metadata?.billing_interval,
      company_name: session.metadata?.company_name,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load session.";
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
