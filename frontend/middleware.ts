import NextAuth from "next-auth";
import { NextResponse } from "next/server";

import { authConfig } from "@/auth.config";
import { sitePageUrl } from "@/lib/site";

const { auth } = NextAuth(authConfig);

/** HTTP Link canonical reinforces HTML <link rel="canonical"> for indexable marketing URLs. */
function withCanonicalLink(pathname: string, res: NextResponse) {
  if (
    pathname === "/blog" ||
    pathname.startsWith("/blog/") ||
    pathname === "/glossary" ||
    pathname.startsWith("/glossary/")
  ) {
    const canonical = sitePageUrl(pathname);
    res.headers.set("Link", `<${canonical}>; rel="canonical"`);
  }
  return res;
}

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

  return withCanonicalLink(pathname, NextResponse.next());
});

export const config = {
  matcher: [
    "/app/:path*",
    "/account/:path*",
    "/forecast-engine/:path*",
    "/board",
    "/blog",
    "/blog/:path*",
    "/glossary",
    "/glossary/:path*",
  ],
};
