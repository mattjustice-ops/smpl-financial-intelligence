import type { Metadata } from "next";
import "./globals.css";

import { AuthProvider } from "@/components/providers/AuthProvider";

export const metadata: Metadata = {
  title: "SMPL.ai · CFO Operating Intelligence",
  description: "Live executive operating review — SaaS financial intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
