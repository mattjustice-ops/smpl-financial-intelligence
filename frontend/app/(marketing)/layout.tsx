import type { Metadata } from "next";

import "./landing.css";

export const metadata: Metadata = {
  title: "SMPL.ai · Financial intelligence for SaaS operators",
  description:
    "Connect pipeline, ARR, revenue, cash, headcount, and financial statements into one trusted platform for SaaS finance teams.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <div className="marketing-root">{children}</div>;
}
