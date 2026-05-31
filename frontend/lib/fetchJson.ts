export async function fetchJson<T>(
  url: string,
  init?: RequestInit,
  timeoutMs = 15000
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      cache: init?.cache ?? "no-store",
      headers: {
        "Cache-Control": "no-cache",
        ...(init?.headers ?? {}),
      },
    });
    const text = await res.text();
    if (!res.ok) {
      if (res.status === 404 && url.includes("management-pl")) {
        const target = res.headers.get("X-SFI-Proxy-Target");
        throw new Error(
          `${url} returned 404. ` +
            (target ? `Next proxied to: ${target}. ` : "") +
            `Open http://127.0.0.1:8000/api/v1/management-pl/ping — expect build management-pl-v4-inline. ` +
            `Restart backend (backend\\.\\start-api.ps1) and frontend (npm run dev). Response: ${text}`
        );
      }
      throw new Error(`${url} returned ${res.status}: ${text}`);
    }
    return JSON.parse(text) as T;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Timed out after ${timeoutMs}ms: ${url}`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}
