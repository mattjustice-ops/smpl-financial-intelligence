"use client";

import { useState } from "react";

import { LeadIntakeForm } from "@/components/request-quote/LeadIntakeForm";

export function BookDemoContent({ preferredPlan }: { preferredPlan?: string }) {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="px-6 py-16 md:py-24">
      <div className="mx-auto max-w-4xl">
        {!submitted ? (
          <div className="mb-10 max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">Book a demo</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
              See SMPL with your priorities in mind.
            </h1>
            <p className="mt-4 text-lg text-slate-400">
              We use the same intake as request a quote so our team has context before your call. After you
              submit, you&apos;ll go straight to our calendar to pick a time.
            </p>
          </div>
        ) : null}
        <LeadIntakeForm
          intent="demo"
          preferredTier={preferredPlan}
          onDemoSubmitted={() => setSubmitted(true)}
        />
      </div>
    </div>
  );
}
