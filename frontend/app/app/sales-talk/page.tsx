import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { SalesTalkTrack } from "@/components/sales-talk/SalesTalkTrack";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export const metadata = {
  title: "SMPL · Sales Talk Track",
};

export default async function SalesTalkPage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/sales-talk");
  }

  if (!isSmplOpsAdminEmail(session.user.email)) {
    return (
      <main className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-xl font-semibold text-white">Sales Talk Track</h1>
        <p className="mt-3 text-sm text-slate-400">
          This page is restricted to internal SMPL sales/ops admins. Add your email to{" "}
          <code className="text-teal-300">SMPL_OPS_ADMIN_EMAILS</code> on Vercel (or locally in{" "}
          <code className="text-teal-300">.env.local</code>).
        </p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <SalesTalkTrack />
    </div>
  );
}
