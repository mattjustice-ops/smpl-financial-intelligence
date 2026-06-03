import type { Metadata } from "next";

import "./landing.css";

export const metadata: Metadata = {
  title: "SMPL.ai · AI operating system for SaaS finance teams",
  description:
    "SMPL connects pipeline, ARR, revenue, cash, headcount, and financial statements into one intelligent operating model — governed, board-ready, and built for executive decisions.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing-root min-h-screen bg-slate-950 text-white antialiased">
      {children}
    </div>
  );
}
