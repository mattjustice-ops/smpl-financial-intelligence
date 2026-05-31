import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
