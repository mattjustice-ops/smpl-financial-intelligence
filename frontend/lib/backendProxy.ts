import { NextRequest, NextResponse } from "next/server";

export function backendUrl(): string {
  const raw =
    process.env.SFI_BACKEND_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

/** Server-side proxy from Next → FastAPI (avoids rewrite / CORS issues). */
export async function proxyToBackend(
  request: NextRequest,
  apiPath: string
): Promise<NextResponse> {
  const search = request.nextUrl.search;
  const url = `${backendUrl()}${apiPath}${search}`;
  const method = request.method.toUpperCase();
  try {
    const init: RequestInit = { cache: "no-store", method };
    if (method !== "GET" && method !== "HEAD") {
      init.body = await request.arrayBuffer();
      const contentType = request.headers.get("content-type");
      if (contentType) {
        init.headers = { "Content-Type": contentType };
      }
    }
    const res = await fetch(url, init);
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
        "X-SFI-Proxy-Target": url,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      {
        detail: `Proxy failed: ${message}`,
        proxy_target: url,
        hint: "Start backend: cd backend; .\\start-api.ps1",
      },
      { status: 502 }
    );
  }
}
