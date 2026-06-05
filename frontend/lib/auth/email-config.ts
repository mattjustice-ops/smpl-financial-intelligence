export function getEmailFrom(): string {
  return process.env.EMAIL_FROM?.trim() || "onboarding@resend.dev";
}

/** Env-only check safe for RSC pages (no filesystem reads). */
export function isRealEmailConfigured(): boolean {
  return Boolean(
    process.env.AUTH_RESEND_KEY?.trim() ||
      process.env.RESEND_API_KEY?.trim() ||
      process.env.RESEND_TOKEN_FILE?.trim() ||
      process.env.EMAIL_SERVER?.trim()
  );
}
