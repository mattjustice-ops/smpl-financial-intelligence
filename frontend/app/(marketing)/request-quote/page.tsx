import type { Metadata } from "next";

import { RequestQuoteForm } from "@/components/request-quote/RequestQuoteForm";

import { sitePageUrl } from "@/lib/site";

const title = "Request a Quote | SMPL.ai Pricing & Packaging";
const description =
  "Tell us your finance stack and goals. We'll recommend the right SMPL.ai package for SaaS FP&A, reporting, and board readiness.";
const url = sitePageUrl("/request-quote");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
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
