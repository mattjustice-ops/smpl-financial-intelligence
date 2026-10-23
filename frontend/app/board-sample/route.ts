import { NextResponse } from "next/server";

/** The public sample board is closed. Old links go to book a demo. */
export function GET(request: Request) {
  return NextResponse.redirect(new URL("/book-demo", request.url), 308);
}
