function isLocalhostUrl(url: string): boolean {
  return /127\.0\.0\.1|localhost/i.test(url);
}

/**
 * API base for browser `fetch`.
 * Deployed browsers always get same-origin `/api/v1/*`, handled by the authenticated
 * App Router proxy (app/api/v1/[...path]). Direct backend URLs are for local dev and server code.
 */
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host && !isLocalhostUrl(host)) {
      return "";
    }
  }

  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (raw && !isLocalhostUrl(raw)) {
    return raw.replace(/\/$/, "");
  }

  return raw?.replace(/\/$/, "") || "http://127.0.0.1:8000";
}

/** Same-origin base for routes implemented as Next.js API handlers. */
export function getNextApiBase(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return getApiBase();
}

/**
 * Long-running board/export calls. Same-origin when deployed: the browser never calls
 * Railway directly, because only the Next proxy carries the session and internal key.
 * The proxy routes for these calls allow up to 300s.
 */
export function getLongRunningApiBase(): string {
  return getApiBase();
}

/** Workforce routes proxy through Next.js → backend (see app/api/v1/workforce/[...path]). */
export function getWorkforceApiBase(): string {
  return getNextApiBase();
}

/** Human-readable API target for UI. */
export function getApiBaseDisplay(): string {
  const backend = getApiBase();
  if (typeof window !== "undefined") {
    const label = backend || `${window.location.origin} (Next proxy /api/v1)`;
    return `${label} · Management P&L via Next proxy /api/v1/management-pl`;
  }
  return backend || "same-origin /api/v1 proxy";
}

/** FastAPI `date` query param (YYYY-MM-DD). Accepts YYYY-MM or YYYY-MM-DD. */
export function toApiDateParam(period: string): string {
  const trimmed = period.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed;
  if (/^\d{4}-\d{2}$/.test(trimmed)) return `${trimmed}-01`;
  return trimmed;
}

export function formatFetchError(error: unknown, url: string): string {
  if (error instanceof Error) {
    if (error.name === "AbortError") {
      return (
        `Timed out waiting for ${url} (5 min limit). ` +
        `If the backend terminal still shows activity, wait and retry; otherwise check uvicorn logs for errors.`
      );
    }
    if (error.message === "Failed to fetch" || error.message.includes("NetworkError")) {
      const base = getApiBase();
      return (
        `Network error calling ${url}. ` +
        `1) Start API: backend\\start-api.ps1 (Postgres up first). ` +
        `2) Confirm ${base || "http://127.0.0.1:8000"}/health in the browser. ` +
        `3) Restart Next.js dev server after changing next.config.js or .env.local. ` +
        `4) Watch the uvicorn terminal when opening Management P&L — a Python traceback there means a backend crash.`
      );
    }
    return error.message;
  }
  return String(error);
}
