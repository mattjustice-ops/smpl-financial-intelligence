import Link from "next/link";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { isRealEmailConfigured } from "@/lib/auth/email-config";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  const emailConfigured = isRealEmailConfigured();

  return (
    <div className="marketing-root min-h-screen bg-slate-950 text-white antialiased">
      <LandingHeader />
      <div className="flex justify-center px-4 py-10 md:py-12">
        <div className="mx-auto w-full max-w-[18rem] rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-5 shadow-xl sm:max-w-[19rem] sm:p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-teal-400">Customer login</p>
          <h1 className="mt-1.5 text-xl font-semibold tracking-tight">Sign in to SMPL</h1>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            For customers with a workspace. We&apos;ll email a secure sign-in link to your work address.
          </p>

          <div className="mt-5">
            <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
              <LoginForm emailConfigured={emailConfigured} />
            </Suspense>
          </div>

          <p className="mt-5 text-center text-[11px] leading-relaxed text-slate-500">
            Need access?{" "}
            <Link href="/book-demo" className="text-teal-300 hover:text-teal-200">
              Book a demo
            </Link>{" "}
            or{" "}
            <Link href="/request-quote" className="text-teal-300 hover:text-teal-200">
              request pricing
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
