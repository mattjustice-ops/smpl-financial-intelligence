import type { Metadata } from "next";

import { sitePageUrl } from "@/lib/site";

const title = "Checkout complete | SMPL.ai";
const description = "Your SMPL.ai subscription checkout status.";
const url = sitePageUrl("/billing/success");

/** Stripe return URL — keep out of the index. */
export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  robots: { index: false, follow: false },
};

export default function BillingSuccessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
