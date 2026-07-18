import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit .next/standalone so the Docker image ships only the traced runtime files
  // instead of the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
