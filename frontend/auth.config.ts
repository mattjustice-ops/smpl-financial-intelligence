import type { NextAuthConfig } from "next-auth";

/** Edge-safe auth config for middleware (no Node fs/pg/email imports). */
export const authConfig = {
  trustHost: true,
  secret: process.env.AUTH_SECRET,
  session: { strategy: "jwt" as const },
  pages: {
    signIn: "/login",
    verifyRequest: "/login/check-email",
    error: "/login",
  },
  providers: [],
} satisfies NextAuthConfig;
