// Intermediario del reporte semanal: /api/reporting/weekly-location-performance → <origen de la API>/reporting/weekly-location-performance.
// La API sirve /reporting fuera de /api/v1, así que el catch-all (que reenvía a API_BASE_URL) no llega.
// Solo GET: el backoffice no dispara corridas del pipeline. El token se reenvía tal cual y la API exige
// rol admin o manager.

import { apiOrigin, proxyToApi } from "@/lib/bff/proxy";

export async function GET(request: Request) {
  const { search } = new URL(request.url);
  return proxyToApi(
    request,
    (apiBaseUrl) => `${apiOrigin(apiBaseUrl)}/reporting/weekly-location-performance${search}`,
    "GET /reporting/weekly-location-performance"
  );
}
