import type { Metadata } from "next";

import { LeadIntakeForm } from "@/components/request-quote/LeadIntakeForm";

export const metadata: Metadata = {
  title: "Book a demo · SMPL.ai",
  description:
    "Share your contact details and priorities, then schedule a live SMPL demo with our team.",
};

export default function BookDemoPage({
  searchParams,
}: {
  searchParams?: { plan?: string };
}) {
  return (
    <div className="px-6 py-16 md:py-24">
      <div className="mx-auto max-w-4xl">
        <div className="mb-10 max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">Book a demo</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            See SMPL with your priorities in mind.
          </h1>
          <p className="mt-4 text-lg text-slate-400">
            We use the same intake as request a quote so our team has context before your call. When you
            continue to scheduling, we save your details and open our calendar to pick a time.
          </p>
        </div>
        <LeadIntakeForm intent="demo" preferredTier={searchParams?.plan} />
      </div>
    </div>
  );
}
