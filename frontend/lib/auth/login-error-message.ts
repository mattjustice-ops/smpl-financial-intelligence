/** Map Auth.js /login?error= query values to user-facing copy. */

const LOGIN_ERROR_MESSAGES: Record<string, string> = {
  AccessDenied:
    "That email does not have workspace access yet. Use the address from your SMPL invite or checkout.",
  Configuration:
    "Sign-in is not fully configured on the server. On Vercel, set AUTH_SECRET, AUTH_URL, AUTH_RESEND_KEY, and AUTH_DATABASE_URL (Neon/Supabase — not localhost), then redeploy.",
  Verification:
    "This sign-in link expired or was already used. Request a new link from the login page.",
  MissingCSRF: "Your session expired. Refresh the page and try again.",
  OAuthCallbackError: "Sign-in callback failed. Try again or request a new magic link.",
  CredentialsSignin: "Sign-in failed. Check your email and try again.",
};

export function getLoginErrorMessage(errorCode: string | null | undefined, reason?: string | null): string {
  if (errorCode === "AccessDenied" && reason?.trim()) {
    return reason.trim();
  }

  if (errorCode && LOGIN_ERROR_MESSAGES[errorCode]) {
    return LOGIN_ERROR_MESSAGES[errorCode];
  }

  if (errorCode === "EmailSignInError" || errorCode === "EmailSignin") {
    return "We could not send the sign-in email. With onboarding@resend.dev, use the exact email on your Resend account.";
  }

  if (errorCode) {
    return `Sign-in failed (${errorCode}). Request a new magic link or contact support.`;
  }

  return "Sign-in failed. Please try again or contact support.";
}

export function parseAuthErrorFromUrl(redirectUrl: string): { error: string | null; reason: string | null } {
  try {
    const url = new URL(redirectUrl, "http://localhost");
    return {
      error: url.searchParams.get("error"),
      reason: url.searchParams.get("reason"),
    };
  } catch {
    if (redirectUrl.includes("error=AccessDenied")) {
      return { error: "AccessDenied", reason: null };
    }
    if (redirectUrl.includes("error=Configuration")) {
      return { error: "Configuration", reason: null };
    }
    return { error: null, reason: null };
  }
}
