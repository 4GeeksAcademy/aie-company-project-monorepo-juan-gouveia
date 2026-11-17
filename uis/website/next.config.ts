import type { NextConfig } from "next";

// Solo en Docker (docker-compose.yml la define): los bind mounts desde Windows y macOS no propagan
// los eventos de archivos, así que Turbopack vigila los cambios por sondeo. Fuera de Docker no se usa.
const pollIntervalMs = Number(process.env.NEXT_WATCH_POLL_INTERVAL_MS) || undefined;

const nextConfig: NextConfig = {
  ...(pollIntervalMs && { watchOptions: { pollIntervalMs } }),
};

export default nextConfig;
