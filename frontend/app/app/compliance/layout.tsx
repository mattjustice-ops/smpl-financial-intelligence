import { LandingHeader } from "@/components/landing/LandingHeader";
import "../../(marketing)/landing.css";

/**
 * Same visual chrome as public marketing pages (e.g. /progress): LandingHeader + marketing-root.
 * Auth / ops-admin gating stays on page.tsx — this route is not public.
 */
export default function AppComplianceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing-root min-h-screen bg-slate-950 text-white antialiased">
      <LandingHeader />
      {children}
    </div>
  );
}
