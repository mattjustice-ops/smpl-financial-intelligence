import Link from "next/link";

import { PRICING_TIERS, bookDemoHref, requestQuoteHref, type PricingTierId } from "@/lib/billing/plans";

type Props = {
  tier: PricingTierId;
  highlighted?: boolean;
};

export function PricingPlanCard({ tier, highlighted }: Props) {
  const plan = PRICING_TIERS[tier];
  const isEnterprise = tier === "enterprise";

  return (
    <div
      className={`flex h-full flex-col rounded-3xl border p-8 shadow-xl shadow-black/20 ${
        highlighted
          ? "border-cyan-400/40 bg-slate-900/80 ring-1 ring-cyan-400/20"
          : "border-white/10 bg-slate-900/50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-2xl font-semibold text-white">{plan.name}</h2>
        <span className="shrink-0 rounded-full border border-teal-400/30 bg-teal-400/10 px-3 py-1 text-xs font-medium text-teal-200">
          {plan.support}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-slate-400">{plan.pricingNote}</p>

      <ul className="mt-6 flex-1 space-y-2 text-sm text-slate-300">
        {plan.highlights.map((feature) => (
          <li key={feature} className="flex gap-2">
            <span className="text-teal-400" aria-hidden>
              •
            </span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      {plan.moduleNames && plan.moduleNames.length > 0 ? (
        <div className="mt-6 border-t border-white/10 pt-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            All platform modules
          </p>
          <ul className="mt-3 grid gap-1.5 text-sm text-slate-400 sm:grid-cols-2">
            {plan.moduleNames.map((name) => (
              <li key={name} className="flex gap-2">
                <span className="text-cyan-400" aria-hidden>
                  ✓
                </span>
                <span>{name}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-8 flex flex-col gap-3">
        <Link
          href={bookDemoHref(tier)}
          className="inline-flex justify-center rounded-full bg-gradient-to-r from-teal-400 to-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
        >
          Book a demo
        </Link>
        <Link
          href={requestQuoteHref(tier)}
          className={`inline-flex justify-center rounded-full px-6 py-3 text-sm font-semibold transition ${
            isEnterprise
              ? "border border-cyan-400/70 text-teal-300 hover:bg-teal-400/10"
              : "border border-white/15 text-white hover:bg-white/5"
          }`}
        >
          {isEnterprise ? "Request quote" : "Request pricing"}
        </Link>
      </div>
    </div>
  );
}
