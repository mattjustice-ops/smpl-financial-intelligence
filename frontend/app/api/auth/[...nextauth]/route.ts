import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

async function respond(method: "GET" | "POST", request: NextRequest) {
  try {
    const { handlers } = await import("@/auth");
    return await (method === "GET" ? handlers.GET(request) : handlers.POST(request));
  } catch (error) {
    console.error("[auth] route failed", error);
    if (method === "GET") {
      return NextResponse.json(null);
    }
    const message = error instanceof Error ? error.message : "Sign-in failed.";
    return NextResponse.json({ message }, { status: 500 });
  }
}

export function GET(request: NextRequest) {
  return respond("GET", request);
}

export function POST(request: NextRequest) {
  return respond("POST", request);
}
