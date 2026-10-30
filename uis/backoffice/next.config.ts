import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // @repo/brasa-core se publica como TypeScript sin compilar y vive fuera de este proyecto.
  transpilePackages: ["@repo/brasa-core"],
  turbopack: {
    root: path.join(__dirname, "../.."),
  },
};

export default nextConfig;
