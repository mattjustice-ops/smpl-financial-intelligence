import NextAuth from "next-auth";
import { NextResponse } from "next/server";

import { authConfig } from "@/auth.config";

const { auth } = NextAuth(authConfig);

/**
 * Auth + board redirects only.
 * Canonicals live in route metadata (HTML <link rel="canonical">). Avoid setting
 * duplicate HTTP Link: rel=canonical here — Vercel/Next already emit them for
 * blog/glossary and double headers confuse crawlers.
 */
export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isProtected =
    pathname.startsWith("/app") ||
    pathname.startsWith("/account") ||
    pathname.startsWith("/forecast-engine");

  if (pathname === "/board" && req.auth) {
    return NextResponse.redirect(new URL("/app/board", req.nextUrl.origin));
  }

  // Public marketing should not expose the live board demo at /board.
  if (pathname === "/board" && !req.auth) {
    return NextResponse.redirect(new URL("/board-sample", req.nextUrl.origin));
  }

  if (isProtected && !req.auth) {
    const loginUrl = new URL("/login", req.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    "/app/:path*",
    "/account/:path*",
    "/forecast-engine/:path*",
    "/board",
  ],
};
