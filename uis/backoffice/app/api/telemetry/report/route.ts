// Intermediario del reporte técnico de telemetría: /api/telemetry/report → <origen de la API>/telemetry/report.
// La API sirve /telemetry fuera de /api/v1, así que el catch-all (que reenvía a API_BASE_URL) no llega.
// Solo GET: el receptor de eventos (POST /telemetry/events) lo llama el navegador directamente.
// El token se reenvía tal cual y la API exige rol admin.

import { apiOrigin, proxyToApi } from "@/lib/bff/proxy";

export async function GET(request: Request) {
  const { search } = new URL(request.url);
  return proxyToApi(request, (apiBaseUrl) => `${apiOrigin(apiBaseUrl)}/telemetry/report${search}`, "GET /telemetry/report");
}
