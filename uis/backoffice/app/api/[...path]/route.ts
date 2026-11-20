// Intermediario (Backend for Frontend) entre el navegador y la API de Brasaland: /api/<ruta> se
// reenvía a API_BASE_URL/<ruta> (la API bajo /api/v1). El reenvío está en lib/bff/proxy.ts.
// El reporte técnico de telemetría, que la API sirve fuera de /api/v1, tiene su propia ruta
// (app/api/telemetry/report/route.ts), que Next.js elige antes que este catch-all.

import { proxyToApi } from "@/lib/bff/proxy";

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function forward(request: Request, { params }: RouteContext) {
  const { path } = await params;
  const { search } = new URL(request.url);
  return proxyToApi(
    request,
    (apiBaseUrl) => `${apiBaseUrl}/${path.map(encodeURIComponent).join("/")}${search}`,
    `${request.method} /${path.join("/")}`,
  );
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
