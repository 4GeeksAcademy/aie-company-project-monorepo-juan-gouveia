// Intermediario de la última corrida del pipeline: /api/reporting/pipeline-runs/latest → <origen de la API>/reporting/pipeline-runs/latest.
// Fuera de /api/v1, como el reporte semanal. Solo GET; el token se reenvía tal cual y la API exige rol
// admin o manager.

import { apiOrigin, proxyToApi } from "@/lib/bff/proxy";

export async function GET(request: Request) {
  return proxyToApi(
    request,
    (apiBaseUrl) => `${apiOrigin(apiBaseUrl)}/reporting/pipeline-runs/latest`,
    "GET /reporting/pipeline-runs/latest"
  );
}
