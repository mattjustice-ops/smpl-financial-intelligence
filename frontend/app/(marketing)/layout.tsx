import type { Metadata } from "next";

import { LandingHeader } from "@/components/landing/LandingHeader";
import { SITE_DESCRIPTION, SITE_TITLE } from "@/lib/site";
import "./landing.css";

/**
 * Shared marketing chrome + soft defaults.
 * Do not set alternates.canonical here — every indexable route must declare its
 * own absolute canonical (homepage included via page.tsx). A layout-level
 * homepage canonical made child URLs look like duplicates of `/`.
 */
export const metadata: Metadata = {
  title: {
    absolute: SITE_TITLE,
  },
  description: SITE_DESCRIPTION,
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing-root min-h-screen bg-slate-950 text-white antialiased">
      <LandingHeader />
      {children}
    </div>
  );
}
