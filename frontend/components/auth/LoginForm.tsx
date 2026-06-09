"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { requestMagicLink } from "@/app/login/actions";
import { getLoginErrorMessage } from "@/lib/auth/login-error-message";

type LoginFormProps = {
  emailConfigured: boolean;
};

export function LoginForm({ emailConfigured }: LoginFormProps) {
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("error");
  const accessReason = searchParams.get("reason");
  const callbackUrl = searchParams.get("callbackUrl") ?? "/app";
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const result = await requestMagicLink(email, callbackUrl);

      if (!result.ok) {
        setError(result.message);
        return;
      }

      window.location.assign(result.redirectTo);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
      {error || errorCode ? (
        <div className="rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-2.5 text-xs text-red-200">
          {error ??
            getLoginErrorMessage(errorCode, accessReason)}
        </div>
      ) : null}

      <div>
        <label htmlFor="email" className="mb-1 block text-xs font-medium text-slate-200">
          Work email
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@company.com"
          className="w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-teal-400/50 focus:ring-2 focus:ring-teal-400/20"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="inline-flex h-10 w-full items-center justify-center rounded-full bg-teal-400 text-sm font-semibold text-slate-950 transition hover:bg-teal-300 disabled:opacity-60"
      >
        {submitting ? "Sending link…" : "Email me a sign-in link"}
      </button>

      {emailConfigured ? (
        <p className="text-center text-[10px] leading-relaxed text-slate-500">
          We&apos;ll send a secure sign-in link to your inbox. The subject line is{" "}
          <strong className="font-medium text-slate-400">Your SMPL sign-in link</strong>. Check spam if
          it doesn&apos;t arrive within a minute.
        </p>
      ) : (
        <p className="text-center text-[10px] leading-relaxed text-slate-500">
          Email is not configured yet. Run{" "}
          <code className="text-slate-400">.\scripts\setup-resend-email.ps1</code> and restart{" "}
          <code className="text-slate-400">npm run dev</code>.
        </p>
      )}
    </form>
  );
}
