"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

function SuccessContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState<"loading" | "complete" | "pending" | "error">("loading");
  const [details, setDetails] = useState<{ plan?: string; company_name?: string }>({});

  useEffect(() => {
    if (!sessionId) {
      setStatus("error");
      return;
    }

    fetch(`/api/billing/session?session_id=${encodeURIComponent(sessionId)}`)
      .then((res) => res.json())
      .then((data: { ok?: boolean; payment_status?: string; plan?: string; company_name?: string }) => {
        if (!data.ok) {
          setStatus("error");
          return;
        }
        setDetails({ plan: data.plan, company_name: data.company_name });
        if (data.payment_status === "paid" || data.payment_status === "no_payment_required") {
          setStatus("complete");
        } else {
          setStatus("pending");
        }
      })
      .catch(() => setStatus("error"));
  }, [sessionId]);

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-2xl flex-col justify-center px-6 py-16 text-center">
      <h1 className="text-3xl font-semibold text-white md:text-4xl">
        {status === "complete" ? "Payment successful" : "Processing your subscription"}
      </h1>
      <p className="mt-4 text-slate-400">
        {status === "complete"
          ? "Your SMPL workspace is being prepared. You will receive onboarding instructions shortly."
          : status === "pending"
            ? "Stripe is confirming payment. Refresh this page in a moment or contact support if it takes longer than a few minutes."
            : "We could not verify your checkout session. Contact support with your receipt email."}
      </p>
      {details.company_name ? (
        <p className="mt-2 text-sm text-teal-300">
          {details.company_name}
          {details.plan ? ` · ${details.plan} plan` : ""}
        </p>
      ) : null}

      <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
        <Link
          href="/app"
          className="inline-flex rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-8 py-3 text-sm font-semibold text-slate-950"
        >
          Go to dashboard
        </Link>
        <Link
          href="/account/billing"
          className="inline-flex rounded-full border border-white/15 px-8 py-3 text-sm font-medium text-white hover:bg-white/5"
        >
          View billing
        </Link>
      </div>

      {status === "pending" ? (
        <p className="mt-8 text-xs text-slate-500">
          Provisioning may take up to a minute while webhooks sync your subscription.
        </p>
      ) : null}
    </main>
  );
}

export default function BillingSuccessPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Suspense
        fallback={
          <main className="mx-auto max-w-2xl px-6 py-16 text-center text-slate-400">
            Loading checkout status…
          </main>
        }
      >
        <SuccessContent />
      </Suspense>
    </div>
  );
}
