/** @type {import('next').NextConfig} */
const backendUrl = (
  process.env.SFI_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8001"
).replace(/\/$/, "");

const isLocalBackend = /127\.0\.0\.1|localhost/i.test(backendUrl);

// /api/v1/*, /health, and /health/db are proxied by App Router route handlers at
// *runtime* using SFI_BACKEND_URL. Skip build-time rewrites on Vercel when the
// API URL is not configured yet (otherwise rewrites point at localhost).
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.sanity.io",
      },
    ],
  },
  async rewrites() {
    if (process.env.VERCEL && isLocalBackend) {
      console.warn(
        "[next.config] SFI_BACKEND_URL not set at build time — skipping rewrites; " +
          "App Router proxies use runtime env. Set Preview env vars in Vercel dashboard.",
      );
      return [];
    }
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
      { source: "/health", destination: `${backendUrl}/health` },
      { source: "/health/db", destination: `${backendUrl}/health/db` },
    ];
  },
};

module.exports = nextConfig;
