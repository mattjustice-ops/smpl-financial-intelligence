import { NextResponse } from "next/server";

function backendUrl(): string {
  return (
    process.env.SFI_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8001"
  ).replace(/\/$/, "");
}

export async function GET() {
  try {
    const res = await fetch(`${backendUrl()}/health/db`, { cache: "no-store" });
    const body = await res.text();
    return new NextResponse(body, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { status: "error", message: error instanceof Error ? error.message : String(error) },
      { status: 502 }
    );
  }
}
