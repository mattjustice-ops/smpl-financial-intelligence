import type { Metadata } from "next";

import { ComplianceProgressDashboard } from "@/components/compliance/ComplianceProgressDashboard";
import { sitePageUrl } from "@/lib/site";

const title = "SOC 2 Readiness Progress | SMPL.ai";
const description =
  "SMPL.ai SOC 2 Type I readiness checklist — not certified yet. Track kickoff, controls, and audit progress honestly while we prepare for an independent CPA report.";
const url = sitePageUrl("/compliance");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

export default function CompliancePage() {
  return <ComplianceProgressDashboard />;
}
