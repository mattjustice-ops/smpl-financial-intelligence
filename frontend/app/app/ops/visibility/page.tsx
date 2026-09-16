import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { AioVisibilityDashboard } from "@/components/ops/visibility/AioVisibilityDashboard";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export const metadata = {
  title: "SMPL · AIO Visibility",
};

export default async function AioVisibilityPage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/ops/visibility");
  }

  if (!isSmplOpsAdminEmail(session.user.email)) {
    return (
      <main className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-xl font-semibold text-white">AIO Visibility</h1>
        <p className="mt-3 text-sm text-slate-400">
          Restricted to internal SMPL admins (
          <code className="text-teal-300">SMPL_OPS_ADMIN_EMAILS</code>).
        </p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <AioVisibilityDashboard />
    </div>
  );
}
