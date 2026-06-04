import { PricingPlanCard } from "@/components/billing/PricingPlanCard";
import { PRICING_TIER_ORDER } from "@/lib/billing/plans";

export default function PricingPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-semibold tracking-tight text-white md:text-5xl">
            Plans built for SaaS finance teams
          </h1>
          <p className="mt-4 text-lg text-slate-400">
            Compare capabilities by tier. Every plan includes a dedicated environment, dashboards,
            and AI commentary. Pricing and billing terms are finalized during contracting after
            your demo.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-3">
          {PRICING_TIER_ORDER.map((tier) => (
            <PricingPlanCard key={tier} tier={tier} highlighted={tier === "professional"} />
          ))}
        </div>

        <p className="mx-auto mt-12 max-w-2xl text-center text-sm text-slate-500">
          Implementation scope, integrations beyond your tier allowance, and support upgrades are
          discussed with your team after a walkthrough — not on a self-serve checkout page.
        </p>
    </main>
  );
}
