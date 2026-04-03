import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // CRITICAL: Explicitly transpile internal monorepo packages.
  // Prevents Next.js 15 from treating them as external, which can
  // cause duplicate React instances in the build worker.
  transpilePackages: ["@bharatdata/shared", "@bharatdata/typescript-sdk"],

  // Prevent Leaflet from being bundled into the SSR worker.
  // react-leaflet v5 + leaflet are browser-only by design.
  serverExternalPackages: ["leaflet"],

  reactStrictMode: false,

  experimental: {
    optimizePackageImports: ["framer-motion", "lucide-react"],
  },
};

export default nextConfig;
