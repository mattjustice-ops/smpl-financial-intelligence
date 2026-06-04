import type { Metadata } from "next";

import { RequestQuoteForm } from "@/components/request-quote/RequestQuoteForm";

export const metadata: Metadata = {
  title: "Request a quote · SMPL.ai",
  description:
    "A few quick questions about your stack and goals. SMPL will suggest the right package and coordinate a follow-up on your schedule.",
};

export default function RequestQuotePage({
  searchParams,
}: {
  searchParams?: { plan?: string };
}) {
  return (
    <div className="px-6 py-16 md:py-24">
      <div className="mx-auto max-w-4xl">
        <div className="mb-10 max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">Request a quote</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Get a tailored SMPL package recommendation.
          </h1>
          <p className="mt-4 text-lg text-slate-400">
            Share a few details about your team and priorities. We&apos;ll follow up to schedule a demo and
            discuss the right SMPL plan.
          </p>
        </div>
        <RequestQuoteForm preferredTier={searchParams?.plan} />
      </div>
    </div>
  );
}
