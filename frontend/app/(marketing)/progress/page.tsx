import type { Metadata } from "next";

import { GoLiveProgressDashboard } from "@/components/progress/GoLiveProgressDashboard";
import { sitePageUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: { absolute: "SMPL · Go-live progress" },
  alternates: { canonical: sitePageUrl("/progress") },
  robots: { index: false, follow: false },
};

export default function GoLiveProgressPage() {
  return <GoLiveProgressDashboard />;
}
