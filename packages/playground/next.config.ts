import type { NextConfig } from "next";
import { createRequire } from "module";
import path from "path";

// Use require to resolve React's actual disk location in the npm workspace
const require = createRequire(import.meta.url);

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // CRITICAL: Next.js 15 requires explicit transpilation of monorepo packages.
  transpilePackages: ["@bharatdata/shared", "@bharatdata/typescript-sdk"],
  
  // Prevent Leaflet from being bundled into the SSR worker.
  serverExternalPackages: ["leaflet"],
  
  reactStrictMode: false,
  
  experimental: {
    optimizePackageImports: ["framer-motion", "lucide-react"],
  },

  /**
   * FORCE BUNDLER-LEVEL DEDUPLICATION
   * 
   * Root Cause: node_modules contains a React 19 Release Candidate (RC) 
   * that is being picked up by framer-motion and recharts, conflicting 
   * with the stable version and causing 'useContext null' crashes.
   * 
   * This alias forces EVERY package in the monorepo (and the build worker)
   * to use exactly one physical copy of stable React from the root.
   */
  webpack: (config) => {
    const reactPath = path.dirname(require.resolve("react/package.json"));
    const reactDomPath = path.dirname(require.resolve("react-dom/package.json"));

    config.resolve.alias = {
      ...config.resolve.alias,
      react: reactPath,
      "react-dom": reactDomPath,
    };

    return config;
  },
};

export default nextConfig;
