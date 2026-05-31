/**
 * API base for browser `fetch`.
 * Management P&L uses Next.js route handlers under `/api/v1/management-pl/*` (server proxy).
 * Other calls may use direct backend URL from NEXT_PUBLIC_API_URL.
 */
export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (raw) {
    return raw.replace(/\/$/, "");
  }
  return "http://127.0.0.1:8000";
}

/** Same-origin base for routes implemented as Next.js API handlers. */
export function getNextApiBase(): string {
  if (typeof window !== "undefined") {
    return "";
  }
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
    return `${backend} · Management P&L via Next proxy /api/v1/management-pl`;
  }
  return backend;
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
