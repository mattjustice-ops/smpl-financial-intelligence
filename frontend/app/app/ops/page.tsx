import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { SmplOpsDashboard } from "@/components/ops/SmplOpsDashboard";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export const metadata = {
  title: "SMPL · Ops",
};

export default async function SmplOpsPage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/ops");
  }

  if (!isSmplOpsAdminEmail(session.user.email)) {
    return (
      <main className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-xl font-semibold text-white">SMPL Ops</h1>
        <p className="mt-3 text-sm text-slate-400">
          This page is restricted to internal SMPL admins. Add your email to{" "}
          <code className="text-teal-300">SMPL_OPS_ADMIN_EMAILS</code> on Vercel (or locally in{" "}
          <code className="text-teal-300">.env.local</code>).
        </p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <SmplOpsDashboard />
    </div>
  );
}
