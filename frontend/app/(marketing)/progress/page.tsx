import { GoLiveProgressDashboard } from "@/components/progress/GoLiveProgressDashboard";

export const metadata = {
  title: "SMPL · Go-live progress",
  robots: { index: false, follow: false },
};

export default function GoLiveProgressPage() {
  return <GoLiveProgressDashboard />;
}
