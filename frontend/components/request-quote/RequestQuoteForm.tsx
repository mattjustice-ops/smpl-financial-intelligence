"use client";

import { LeadIntakeForm } from "./LeadIntakeForm";

export function RequestQuoteForm({ preferredTier }: { preferredTier?: string }) {
  return <LeadIntakeForm intent="quote" preferredTier={preferredTier} />;
}
