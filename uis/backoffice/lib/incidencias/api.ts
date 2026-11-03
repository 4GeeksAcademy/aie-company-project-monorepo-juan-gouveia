import type { ApiErrorBody, IncidentAnalysis } from "@/types/incident";

// Rutas del intermediario (app/api/[...path]/route.ts), que las reenvía a la API de Brasaland.
const ANALYZE_URL = "/api/incidents/analyze";
const EXPORT_URL = "/api/incidents/results/export";

// La API responde los errores como { error: { code, message } } con un mensaje en español.
async function errorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body: ApiErrorBody = await res.json();
    if (body.error?.message) return body.error.message;
  } catch {
    // El cuerpo no es JSON: se usa el mensaje genérico.
  }
  return `Error ${res.status}: ${fallback}`;
}

export async function analyzeIncidents(file: File): Promise<IncidentAnalysis> {
  const formData = new FormData();
  formData.append("file", file);

  let res: Response;
  try {
    res = await fetch(ANALYZE_URL, { method: "POST", body: formData });
  } catch {
    throw new Error("No se pudo conectar con el backoffice. Revisa tu conexión.");
  }

  if (!res.ok) {
    throw new Error(await errorMessage(res, "no se pudo analizar el archivo"));
  }

  return res.json();
}

// Descarga el CSV del último análisis. Se comprueba la respuesta antes de guardar nada,
// para no descargar un JSON de error con el nombre results.csv.
export async function downloadResults(): Promise<void> {
  let res: Response;
  try {
    res = await fetch(EXPORT_URL);
  } catch {
    throw new Error("No se pudo conectar con el backoffice. Revisa tu conexión.");
  }

  if (!res.ok) {
    throw new Error(await errorMessage(res, "no se pudo descargar el CSV"));
  }

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
