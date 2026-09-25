import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Demo mode preloads the synthetic demo orders so every screen has data on first open. Set NEXT_PUBLIC_DEMO_MODE=false to disable.
  env: { NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE ?? "true" },
  // The browser only talks to this origin; Next forwards /api/* to the FastAPI backend.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
