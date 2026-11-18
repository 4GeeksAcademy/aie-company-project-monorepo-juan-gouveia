import { apiJson, jsonBody } from "@/lib/api-client";
import type {
  Incident,
  IncidentCreateInput,
  IncidentFilters,
  IncidentStatus,
  IncidentSummary,
} from "@/types/incident-manager";

// Rutas del intermediario (/api/incidents…), que las reenvía a /api/v1/incidents de la API.
const INCIDENTS_PATH = "/incidents";

// POST /incidents: 201 con la incidencia creada (siempre en `open`). Un 400 trae `details` por campo.
export function createIncident(input: IncidentCreateInput): Promise<Incident> {
  return apiJson(INCIDENTS_PATH, {
    fallback: "no se pudo registrar la incidencia",
    ...jsonBody("POST", input),
  });
}

// GET /incidents con los filtros elegidos (los vacíos no se envían). Más reciente primero.
export function listIncidents(filters: IncidentFilters): Promise<Incident[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return apiJson(query ? `${INCIDENTS_PATH}?${query}` : INCIDENTS_PATH, {
    fallback: "no se pudieron cargar las incidencias",
  });
}

// GET /incidents/summary: totales por estado, categoría, origen y sede.
export function getIncidentSummary(): Promise<IncidentSummary> {
  return apiJson(`${INCIDENTS_PATH}/summary`, { fallback: "no se pudo cargar el resumen" });
}

// PATCH /incidents/{id}/status: solo cambia el estado. 400 invalid_transition si el ciclo de vida no lo permite.
export function updateIncidentStatus(id: number, status: IncidentStatus): Promise<Incident> {
  return apiJson(`${INCIDENTS_PATH}/${id}/status`, {
    fallback: "no se pudo cambiar el estado",
    ...jsonBody("PATCH", { status }),
  });
}
