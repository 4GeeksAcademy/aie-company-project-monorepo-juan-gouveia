import { ApiError, apiJson, apiJsonWithRequestId, jsonBody } from "@/lib/api-client";
import { track } from "@/lib/telemetry";
import {
  incidentCreatedProperties,
  incidentStatusChangedProperties,
  incidentTransitionRejectedProperties,
} from "@/lib/telemetry/business-events";
import { withRequestId } from "@/lib/telemetry/request-context";
import type {
  Incident,
  IncidentCreateInput,
  IncidentFilters,
  IncidentListItem,
  IncidentStatus,
  IncidentSummary,
} from "@/types/incident-manager";

// Rutas del intermediario (/api/incidents…), que las reenvía a /api/v1/incidents de la API.
//
// Telemetría (plan, §5.6): el alta y el cambio de estado emiten su evento al recibir la respuesta,
// con el `requestId` de esa llamada; un cambio de estado rechazado (400 invalid_transition) emite
// `incident_transition_rejected`. Para el estado, quien llama pasa la incidencia tal como estaba.
const INCIDENTS_PATH = "/incidents";

function emit(requestId: string | null, eventType: string, properties: Record<string, unknown>) {
  try {
    withRequestId(requestId, () => track(eventType, properties));
  } catch {
    // La telemetría no interfiere con el gestor.
  }
}

// POST /incidents: 201 con la incidencia creada (siempre en `open`). Un 400 trae `details` por campo.
// Telemetría: `incident_created`.
export async function createIncident(input: IncidentCreateInput): Promise<Incident> {
  const { data, requestId } = await apiJsonWithRequestId<Incident>(INCIDENTS_PATH, {
    fallback: "no se pudo registrar la incidencia",
    ...jsonBody("POST", input),
  });
  emit(requestId, "incident_created", incidentCreatedProperties(data));
  return data;
}

// GET /incidents con los filtros elegidos (los vacíos no se envían). Más reciente primero.
export function listIncidents(filters: IncidentFilters): Promise<IncidentListItem[]> {
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
// Telemetría: `incident_status_changed`, o `incident_transition_rejected` si el ciclo de vida no lo permite.
export async function updateIncidentStatus(id: number, status: IncidentStatus, previous?: IncidentListItem): Promise<Incident> {
  try {
    const { data, requestId } = await apiJsonWithRequestId<Incident>(`${INCIDENTS_PATH}/${id}/status`, {
      fallback: "no se pudo cambiar el estado",
      ...jsonBody("PATCH", { status }),
    });
    if (previous) emit(requestId, "incident_status_changed", incidentStatusChangedProperties(previous, data));
    return data;
  } catch (err) {
    if (previous && err instanceof ApiError && err.code === "invalid_transition") {
      emit(err.requestId, "incident_transition_rejected", incidentTransitionRejectedProperties(previous, status));
    }
    throw err;
  }
}
