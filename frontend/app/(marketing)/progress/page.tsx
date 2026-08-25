import type { Metadata } from "next";

import { GoLiveProgressDashboard } from "@/components/progress/GoLiveProgressDashboard";
import { sitePageUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: { absolute: "SMPL · Go-live progress" },
  description: "Internal SMPL.ai go-live progress tracker.",
  alternates: { canonical: sitePageUrl("/progress") },
  robots: { index: false, follow: false },
  openGraph: {
    title: "SMPL · Go-live progress",
    description: "Internal SMPL.ai go-live progress tracker.",
    url: sitePageUrl("/progress"),
  },
};

export default function GoLiveProgressPage() {
  return <GoLiveProgressDashboard />;
}
