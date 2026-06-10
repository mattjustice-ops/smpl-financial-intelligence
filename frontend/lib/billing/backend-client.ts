type BillingBackendInit = Omit<RequestInit, "body"> & {
  body?: Record<string, unknown>;
};

function isLocalhostUrl(url: string): boolean {
  return /127\.0\.0\.1|localhost/i.test(url);
}

/** Resolve hosted API URL for server-side fetches (auth session-sync, billing, etc.). */
export function backendBaseUrl(): string | null {
  const candidates = [
    process.env.SFI_BACKEND_URL?.trim(),
    process.env.NEXT_PUBLIC_API_URL?.trim(),
  ].filter((value): value is string => Boolean(value));

  for (const url of candidates) {
    if (process.env.VERCEL && isLocalhostUrl(url)) {
      continue;
    }
    return url.replace(/\/$/, "");
  }

  // Fallback: call /api/v1/* on the public app origin (Next.js rewrite -> Railway).
  const appBase =
    process.env.APP_BASE_URL?.trim() || process.env.AUTH_URL?.trim();
  if (appBase && process.env.VERCEL) {
    return appBase.replace(/\/$/, "");
  }

  return null;
}

export async function callBillingBackend(
  path: string,
  init: BillingBackendInit = {}
): Promise<Response> {
  const base = backendBaseUrl();
  if (!base) {
    if (process.env.VERCEL) {
      throw new Error(
        "SFI_BACKEND_URL is not configured on Vercel Production. Set it to your Railway API URL and redeploy.",
      );
    }
    throw new Error("SFI_BACKEND_URL is not configured.");
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  const internalKey = process.env.BILLING_INTERNAL_API_KEY?.trim();
  if (internalKey) {
    headers["X-Billing-Internal-Key"] = internalKey;
  }

  return fetch(`${base.replace(/\/$/, "")}${path}`, {
    ...init,
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
}
