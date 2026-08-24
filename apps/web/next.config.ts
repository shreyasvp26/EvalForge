import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for infrastructure/docker/Dockerfile.web (standalone server.js).
  output: "standalone",
  transpilePackages: ["@agent-eval/ui"],
  experimental: {
    optimizePackageImports: ["@agent-eval/ui"],
  },
};

export default nextConfig;
