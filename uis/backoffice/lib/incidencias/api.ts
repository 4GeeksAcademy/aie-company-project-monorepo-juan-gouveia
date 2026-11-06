import { apiFetch, apiJson } from "@/lib/api-client";
import type { IncidentAnalysis } from "@/types/incident";

// Rutas del intermediario, que las reenvía a /api/v1/incidents.
const ANALYZE_PATH = "/incidents/analyze";
const EXPORT_PATH = "/incidents/results/export";

export function analyzeIncidents(file: File): Promise<IncidentAnalysis> {
  const formData = new FormData();
  formData.append("file", file);
  // Sin Content-Type: el navegador lo pone con el boundary del multipart.
  return apiJson(ANALYZE_PATH, {
    fallback: "no se pudo analizar el archivo",
    method: "POST",
    body: formData,
  });
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
