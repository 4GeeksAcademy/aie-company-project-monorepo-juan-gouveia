// Intermediario del reporte técnico de telemetría: /api/telemetry/report → <origen de la API>/telemetry/report.
// La API sirve /telemetry fuera de /api/v1, así que el catch-all (que reenvía a API_BASE_URL) no llega.
// Solo POST (ticket #DEV-55): encola el reporte y la API responde 202 con el task_id; el estado se
// consulta en /api/tasks/{taskId}. El receptor de eventos (POST /telemetry/events) lo llama el
// navegador directamente. El token se reenvía tal cual y la API exige rol admin.

import { apiOrigin, proxyToApi } from "@/lib/bff/proxy";

export async function POST(request: Request) {
  return proxyToApi(request, (apiBaseUrl) => `${apiOrigin(apiBaseUrl)}/telemetry/report`, "POST /telemetry/report");
}
