"use client";

import Link from "next/link";

import { PROFESSIONAL_ONLY_SECTIONS } from "@/lib/entitlements/plan-modules";

type Props = {
  planLabel: string;
  visible: boolean;
};

export function PlanUpgradeBanner({ planLabel, visible }: Props) {
  if (!visible) return null;

  const labels = PROFESSIONAL_ONLY_SECTIONS.map((id) =>
    id === "management-pl" ? "Management P&L" : id === "cash" ? "Cash Forecast" : "Workforce",
  );

  return (
    <div
      className="rounded-lg border border-amber-400/25 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/90"
      style={{ marginBottom: 16 }}
    >
      <strong>{planLabel} plan</strong> includes core dashboards and board exports. Upgrade to{" "}
      <strong>Professional</strong> for {labels.join(", ")}.{" "}
      <Link href="/pricing" className="text-teal-300 underline underline-offset-2">
        View plans
      </Link>
    </div>
  );
}
