import type { Metadata } from "next";
import "./globals.css";

import { AuthProvider } from "@/components/providers/AuthProvider";
import { OrganizationJsonLd } from "@/components/seo/OrganizationJsonLd";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL, siteLogoUrl } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} · CFO Operating Intelligence`,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  icons: {
    icon: [
      { url: "/brand/favicon-48.png", type: "image/png", sizes: "48x48" },
      { url: "/brand/smpl-logo.png", type: "image/png", sizes: "512x512" },
    ],
    shortcut: "/brand/favicon-48.png",
    apple: [{ url: "/brand/apple-touch-icon.png", sizes: "192x192" }],
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: [{ url: siteLogoUrl("/brand/smpl-logo.png"), width: 512, height: 512, alt: SITE_NAME }],
  },
  twitter: {
    card: "summary",
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: [siteLogoUrl("/brand/smpl-logo.png")],
  },
  alternates: {
    canonical: SITE_URL,
  },
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
