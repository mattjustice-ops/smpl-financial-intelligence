import { Suspense } from "react";

import { AccountBilling } from "@/components/billing/AccountBilling";

export default function AccountBillingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased">
      <Suspense fallback={<main className="px-6 py-16 text-slate-400">Loading billing…</main>}>
        <AccountBilling />
      </Suspense>
    </div>
  );
}
