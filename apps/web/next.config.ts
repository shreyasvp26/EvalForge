import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@agent-eval/ui"],
  experimental: {
    optimizePackageImports: ["@agent-eval/ui"],
  },
};

export default nextConfig;
