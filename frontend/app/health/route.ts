import { NextResponse } from "next/server";

import { backendBaseUrl } from "@/lib/billing/backend-client";

function hostLabel(base: string): string {
  try {
    return new URL(base).host;
  } catch {
    return "invalid-url";
  }
}

export async function GET() {
  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json(
      {
        status: "error",
        message: "SFI_BACKEND_URL is not configured on this Vercel deployment",
        configured_host: null,
        vercel_env: process.env.VERCEL_ENV ?? null,
        hint:
          "Vercel -> Settings -> Environment Variables -> Preview: set SFI_BACKEND_URL to Railway staging URL, then redeploy gl-5b-sandbox",
      },
      { status: 502 },
    );
  }

  const target = `${base}/health`;
  try {
    const res = await fetch(target, {
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    const body = await res.text();
    return new NextResponse(body, {
      status: res.status,
      headers: {
        "Content-Type": "application/json",
        "X-SFI-Proxy-Target-Host": hostLabel(base),
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : String(error),
        configured_host: hostLabel(base),
        target,
        hint: "Staging API works locally? Check Railway sfi-api-staging is online and URL matches SFI_BACKEND_URL on Vercel Preview.",
      },
      { status: 502 },
    );
  }
}
