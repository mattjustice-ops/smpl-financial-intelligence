/** @type {import('next').NextConfig} */
const backendUrl = (
  process.env.SFI_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8001"
).replace(/\/$/, "");

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
