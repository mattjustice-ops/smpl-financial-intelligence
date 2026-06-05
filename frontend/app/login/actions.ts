"use server";

import { AuthError } from "next-auth";

import { signIn } from "@/auth";
import { getAuthEmailProviderId } from "@/lib/auth/email-secrets";

export type RequestMagicLinkResult =
  | { ok: true; redirectTo: string }
  | { ok: false; message: string };

export async function requestMagicLink(
  email: string,
  callbackUrl: string
): Promise<RequestMagicLinkResult> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail) {
    return { ok: false, message: "Enter your work email." };
  }

  const providerId = getAuthEmailProviderId();

  try {
    const redirectUrl = await signIn(providerId, {
      email: normalizedEmail,
      redirect: false,
      redirectTo: callbackUrl || "/app",
    });

    if (typeof redirectUrl === "string") {
      if (redirectUrl.includes("error=AccessDenied") || redirectUrl.includes("error=EmailSignin")) {
        const reason = new URL(redirectUrl, "http://localhost").searchParams.get("reason");
        return {
          ok: false,
          message:
            reason ??
            "We could not send the sign-in email. Check your email address and try again.",
        };
      }

      console.log(`[auth] Magic link flow completed for ${normalizedEmail} via ${providerId}`);
      return { ok: true, redirectTo: redirectUrl };
    }

    return { ok: true, redirectTo: "/login/check-email" };
  } catch (error) {
    console.error("[auth] requestMagicLink failed:", error);

    if (error instanceof AuthError) {
      if (error.type === "EmailSignInError") {
        return {
          ok: false,
          message:
            "We could not send the sign-in email. With onboarding@resend.dev, use the exact email on your Resend account (Resend Settings).",
        };
      }
      return { ok: false, message: error.message || "Sign-in failed. Please try again." };
    }

    if (error instanceof Error) {
      return { ok: false, message: error.message };
    }

    return { ok: false, message: "Something went wrong sending your sign-in link." };
  }
}
