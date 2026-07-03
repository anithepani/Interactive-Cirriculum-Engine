/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Backend API URL (FastAPI on :8000). Browser-side requests proxy via /api.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:8000/:path*" },
    ];
  },
};

module.exports = nextConfig;
