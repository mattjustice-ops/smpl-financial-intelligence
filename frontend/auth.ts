import "server-only";

import NextAuth from "next-auth";
import Nodemailer from "next-auth/providers/nodemailer";
import Resend from "next-auth/providers/resend";
import nodemailer from "nodemailer";

import { authConfig } from "@/auth.config";
import { getEmailFrom, isRealEmailConfigured } from "@/lib/auth/email-config";
import { getResendApiKey } from "@/lib/auth/email-secrets";
import { AuthPgAdapter } from "@/lib/auth/pg-adapter";
import { getAuthPgPool } from "@/lib/auth/db";
import { sendResendMagicLink } from "@/lib/auth/send-resend-link";
import { syncBackendSession } from "@/lib/auth/sync-backend-session";
import type { BackendOrganization, SendVerificationRequestParams } from "@/lib/auth/types";

async function sendMagicLinkEmail(params: SendVerificationRequestParams) {
  const { identifier, url, provider } = params;
  const from = provider.from ?? getEmailFrom();

  if (!isRealEmailConfigured()) {
    console.log("");
    console.log("[auth] Magic link (email not configured - dev mode)");
    console.log(`  Email: ${identifier}`);
    console.log(`  Link:  ${url}`);
    console.log("  Tip: run .\\scripts\\setup-resend-email.ps1 and add a Resend API key.");
    console.log("");
    return;
  }

  const transport = nodemailer.createTransport(process.env.EMAIL_SERVER!);
  await transport.sendMail({
    to: identifier,
    from,
    subject: "Sign in to SMPL.ai",
    text: `Sign in to SMPL.ai\n\n${url}\n\nIf you did not request this, you can ignore this email.`,
    html: `<p>Sign in to SMPL.ai</p><p><a href="${url}">Continue to your workspace</a></p>`,
  });
}

function buildEmailProviders() {
  const resendKey = getResendApiKey();
  if (resendKey) {
    const from = getEmailFrom();
    return [
      Resend({
        apiKey: resendKey,
        from,
        sendVerificationRequest: async (params: SendVerificationRequestParams) => {
          const { identifier, url, provider } = params;
          const apiKey = getResendApiKey();
          if (!apiKey) {
            throw new Error("Resend API key is not configured.");
          }
          await sendResendMagicLink({
            to: identifier,
            url,
            apiKey,
            from: provider.from ?? getEmailFrom(),
          });
        },
      }),
    ];
  }

  return [
    Nodemailer({
      server: process.env.EMAIL_SERVER ?? "smtp://localhost:1025",
      from: getEmailFrom(),
      sendVerificationRequest: sendMagicLinkEmail,
    }),
  ];
}
export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  adapter: AuthPgAdapter(getAuthPgPool()),
  providers: buildEmailProviders(),
  callbacks: {
    async signIn({ user, email }) {
      if (!user.email) return false;

      // Let Auth.js send the magic link first. Workspace access is checked when the
      // user clicks the link (verificationRequest is only set for the email step).
      if (email?.verificationRequest) {
        return true;
      }

      const sync = await syncBackendSession({
        email: user.email,
        name: user.name,
        authSubject: user.id,
      });
      if (!sync.ok) {
        console.error("[auth] session-sync blocked sign-in:", sync.message);
        return `/login?error=AccessDenied&reason=${encodeURIComponent(sync.message)}`;
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user?.email) {
        const sync = await syncBackendSession({
          email: user.email,
          name: user.name,
          authSubject: user.id,
        });
        if (sync.ok) {
          token.userId = sync.data.userId;
          token.activeOrganizationId = sync.data.activeOrganizationId;
          token.organizations = sync.data.organizations;
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        if (typeof token.userId === "string") {
          session.user.id = token.userId;
        }
        if (typeof token.activeOrganizationId === "string") {
          session.user.activeOrganizationId = token.activeOrganizationId;
        }
        session.user.organizations = (token.organizations as BackendOrganization[] | undefined) ?? [];
      }
      return session;
    },
  },
});
