import { useCallback, useState } from "react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { listIncidents, updateIncidentStatus } from "@/lib/gestor-incidencias/api";
import type { IncidentFilters, IncidentListItem, IncidentStatus } from "@/types/incident-manager";
import { toUserMessage } from "@/lib/error-message";

const NO_FILTERS: IncidentFilters = { status: "", origin: "", branch: "" };

// Listado del gestor de incidencias. Vuelve a pedir la lista cuando cambia un filtro, sin recargar
// la página; los filtros los aplica la API (GET /incidents?status=&origin=&branch=). Si cambian los
// filtros antes de que llegue la respuesta, useAsyncData descarta la anterior.
export function useIncidents() {
  const [filters, setFilters] = useState<IncidentFilters>(NO_FILTERS);
  const load = useCallback(() => listIncidents(filters), [filters]);
  const { state, reload, setData } = useAsyncData(load, "No se pudieron cargar las incidencias.");

  function updateFilter<K extends keyof IncidentFilters>(key: K, value: IncidentFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function replaceIncident(updated: IncidentListItem) {
    setData((prev) => prev.map((incident) => (incident.id === updated.id ? updated : incident)));
  }

  // Cambio de estado optimista: la fila muestra el estado nuevo al momento. Si la API lo rechaza o
  // falla, la fila vuelve a ser exactamente la de antes y se devuelve el mensaje para avisar.
  async function changeStatus(incident: IncidentListItem, next: IncidentStatus): Promise<string | null> {
    replaceIncident({ ...incident, status: next });
    try {
      replaceIncident(await updateIncidentStatus(incident.id, next));
      return null;
    } catch (err) {
      replaceIncident(incident);
      return toUserMessage(err, "No se pudo cambiar el estado. Inténtalo de nuevo.");
    }
  }

  return {
    filters,
    updateFilter,
    clearFilters: () => setFilters(NO_FILTERS),
    hasFilters: Boolean(filters.status || filters.origin || filters.branch),
    incidents: state.status === "success" ? state.data : [],
    fetchState: state,
    changeStatus,
    reload,
  };
}
