import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { ComplianceProgressDashboard } from "@/components/compliance/ComplianceProgressDashboard";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export const metadata: Metadata = {
  title: "SMPL · SOC 2 readiness",
  robots: { index: false, follow: false },
};

export default async function AppCompliancePage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/compliance");
  }

  if (!isSmplOpsAdminEmail(session.user.email)) {
    return (
      <main className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-xl font-semibold text-white">SOC 2 readiness</h1>
        <p className="mt-3 text-sm text-slate-400">
          This page is restricted to internal SMPL admins. Add your email to{" "}
          <code className="text-teal-300">SMPL_OPS_ADMIN_EMAILS</code> on Vercel (or locally in{" "}
          <code className="text-teal-300">.env.local</code>).
        </p>
      </main>
    );
  }

  return <ComplianceProgressDashboard />;
}
