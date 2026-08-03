import type { Metadata } from "next";
import "./globals.css";

import { AuthProvider } from "@/components/providers/AuthProvider";
import { OrganizationJsonLd } from "@/components/seo/OrganizationJsonLd";
import { SITE_DESCRIPTION, SITE_NAME, SITE_TITLE, SITE_URL, siteLogoUrl } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_TITLE,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  icons: {
    // Prefer ≥48px PNG for Google SERP (their guideline). Multi-size
    // /favicon.ico remains for legacy browsers.
    icon: [
      { url: "/brand/favicon-48.png", type: "image/png", sizes: "48x48" },
      { url: "/brand/favicon-96.png", type: "image/png", sizes: "96x96" },
      { url: "/brand/icon-512.png", type: "image/png", sizes: "512x512" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    shortcut: "/favicon.ico",
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: siteLogoUrl("/brand/og-image.png"),
        width: 1200,
        height: 630,
        alt: SITE_NAME,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: [siteLogoUrl("/brand/og-image.png")],
  },
  // Do not set a global canonical here — each route should declare its own.
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <OrganizationJsonLd />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
