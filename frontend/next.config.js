/** @type {import('next').NextConfig} */
const backendUrl = (
  process.env.SFI_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8001"
).replace(/\/$/, "");

if (process.env.VERCEL && /127\.0\.0\.1|localhost/i.test(backendUrl)) {
  throw new Error(
    "SFI_BACKEND_URL or NEXT_PUBLIC_API_URL must be set for Vercel builds (Preview and Production). " +
      "Without it, /api/v1 rewrites point at localhost and dashboards fail with DNS_HOSTNAME_RESOLVED_PRIVATE.",
  );
}

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
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
