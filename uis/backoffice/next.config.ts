import path from "node:path";
import type { NextConfig } from "next";

// Solo en Docker (docker-compose.yml la define): los bind mounts desde Windows y macOS no propagan
// los eventos de archivos, así que Turbopack vigila los cambios por sondeo. Fuera de Docker no se usa.
const pollIntervalMs = Number(process.env.NEXT_WATCH_POLL_INTERVAL_MS) || undefined;

const nextConfig: NextConfig = {
  ...(pollIntervalMs && { watchOptions: { pollIntervalMs } }),
  // @repo/brasa-core se publica como TypeScript sin compilar y vive fuera de este proyecto.
  transpilePackages: ["@repo/brasa-core"],
  turbopack: {
    root: path.join(__dirname, "../.."),
  },
};

export default nextConfig;
