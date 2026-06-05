import Link from "next/link";



import { LandingHeader } from "@/components/landing/LandingHeader";
import { isRealEmailConfigured } from "@/lib/auth/email-config";

export default function CheckEmailPage() {

  const emailConfigured = isRealEmailConfigured();



  return (

    <div className="marketing-root min-h-screen bg-slate-950 text-white antialiased">

      <LandingHeader />

      <div className="flex justify-center px-4 py-10 md:py-12">

        <div className="mx-auto w-full max-w-[18rem] rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-5 text-center shadow-xl sm:max-w-[19rem] sm:p-6">

          <h1 className="text-lg font-semibold">Check your email</h1>

          <p className="mt-2 text-xs leading-relaxed text-slate-400">

            {emailConfigured

              ? "We sent a sign-in link to your inbox. Look for \"Your SMPL sign-in link\" and click Continue to SMPL."

              : "Email is not configured yet, so no message was sent to your inbox."}

          </p>

          {!emailConfigured ? (

            <div className="mt-5 rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-left text-xs leading-relaxed text-amber-100/90">

              <p className="font-medium text-amber-50">Enable inbox delivery</p>

              <p className="mt-1">

                Run{" "}

                <code className="text-amber-100">.\scripts\setup-resend-email.ps1</code>, add your Resend API

                key to{" "}

                <code className="text-amber-100">Resend Token.txt</code>, restart{" "}

                <code className="text-amber-100">npm run dev</code>, and try again.

              </p>

            </div>

          ) : null}

          <Link

            href="/login"

            className="mt-6 inline-flex text-sm font-medium text-teal-300 hover:text-teal-200"

          >

            Back to sign in

          </Link>

        </div>

      </div>

    </div>

  );

}


