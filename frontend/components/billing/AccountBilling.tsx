"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type AccountSummary = {
  organization_id: string;
  organization_name: string;
  status: string;
  plan: string | null;
  stripe_customer_id: string | null;
  subscription: {
    status: string;
    billing_interval: string;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  } | null;
};

export function AccountBilling() {
  const searchParams = useSearchParams();
  const organizationId = searchParams.get("organization_id");
  const email = searchParams.get("email");
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8001";

  const loadAccount = useCallback(async () => {
    const params = new URLSearchParams();
    if (organizationId) params.set("organization_id", organizationId);
    else if (email) params.set("email", email);
    else {
      setError("Add ?organization_id= or ?email= to the URL until auth is wired.");
      return;
    }

    const res = await fetch(`${backendUrl}/api/v1/billing/account?${params.toString()}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      setError("Billing account not found.");
      setAccount(null);
      return;
    }
    setAccount((await res.json()) as AccountSummary);
    setError(null);
  }, [backendUrl, email, organizationId]);

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  async function openPortal() {
    setPortalLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/billing/create-portal-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          organization_id: account?.organization_id,
          stripe_customer_id: account?.stripe_customer_id,
          email: email ?? undefined,
        }),
      });
      const data = (await res.json()) as { ok?: boolean; url?: string; error?: string };
      if (!res.ok || !data.url) {
        throw new Error(data.error ?? "Unable to open billing portal.");
      }
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portal failed.");
      setPortalLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-semibold text-white">Billing</h1>
      <p className="mt-2 text-slate-400">Manage your SMPL subscription and invoices.</p>

      {error ? <p className="mt-6 text-sm text-rose-400">{error}</p> : null}

      {account ? (
        <div className="mt-8 space-y-4 rounded-2xl border border-white/10 bg-slate-900/60 p-6">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Organization</span>
            <span className="text-white">{account.organization_name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Plan</span>
            <span className="capitalize text-white">{account.plan ?? "—"}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Status</span>
            <span className="capitalize text-white">{account.status}</span>
          </div>
          {account.subscription ? (
            <>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Billing interval</span>
                <span className="capitalize text-white">{account.subscription.billing_interval}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Next renewal</span>
                <span className="text-white">
                  {account.subscription.current_period_end
                    ? new Date(account.subscription.current_period_end).toLocaleDateString()
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Subscription</span>
                <span className="capitalize text-white">{account.subscription.status}</span>
              </div>
            </>
          ) : null}

          <button
            type="button"
            onClick={openPortal}
            disabled={portalLoading || !account.stripe_customer_id}
            className="mt-4 w-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"
          >
            {portalLoading ? "Opening portal…" : "Manage billing"}
          </button>
        </div>
      ) : null}

      <p className="mt-8 text-sm text-slate-500">
        Need a new plan?{" "}
        <Link href="/pricing" className="text-teal-300 hover:text-white">
          View pricing
        </Link>
      </p>
    </main>
  );
}
