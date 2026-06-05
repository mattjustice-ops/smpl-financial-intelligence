type BillingBackendInit = Omit<RequestInit, "body"> & {
  body?: Record<string, unknown>;
};

export function backendBaseUrl(): string | null {
  return (
    process.env.SFI_BACKEND_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    null
  );
}

export async function callBillingBackend(
  path: string,
  init: BillingBackendInit = {}
): Promise<Response> {
  const base = backendBaseUrl();
  if (!base) {
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
