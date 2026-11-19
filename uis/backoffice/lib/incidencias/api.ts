import { apiFetch, apiJsonWithRequestId } from "@/lib/api-client";
import { track } from "@/lib/telemetry";
import { incidentReportAnalyzedProperties } from "@/lib/telemetry/business-events";
import { withRequestId } from "@/lib/telemetry/request-context";
import type { IncidentAnalysis } from "@/types/incident";

// Rutas del intermediario, que las reenvía a /api/v1/incidents.
const ANALYZE_PATH = "/incidents/analyze";
const EXPORT_PATH = "/incidents/results/export";

// Telemetría: `incident_report_analyzed` con los recuentos y el tamaño del archivo (nunca su nombre
// ni su contenido).
export async function analyzeIncidents(file: File): Promise<IncidentAnalysis> {
  const formData = new FormData();
  formData.append("file", file);
  // Sin Content-Type: el navegador lo pone con el boundary del multipart.
  const { data, requestId } = await apiJsonWithRequestId<IncidentAnalysis>(ANALYZE_PATH, {
    fallback: "no se pudo analizar el archivo",
    method: "POST",
    body: formData,
  });
  try {
    withRequestId(requestId, () => track("incident_report_analyzed", incidentReportAnalyzedProperties(data, file.size)));
  } catch {
    // La telemetría no interfiere con el análisis.
  }
  return data;
}

// Descarga el CSV del último análisis. apiFetch comprueba la respuesta antes de guardar nada,
// para no descargar un JSON de error con el nombre results.csv.
export async function downloadResults(): Promise<void> {
  const res = await apiFetch(EXPORT_PATH, { fallback: "no se pudo descargar el CSV" });

  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "results.csv";
  document.body.append(link);
  link.click();
  link.remove();
  // Se libera después, para que el navegador haya empezado la descarga.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
