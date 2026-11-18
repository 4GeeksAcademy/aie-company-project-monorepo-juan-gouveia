import { useEffect, useState } from "react";
import { listIncidents, updateIncidentStatus } from "@/lib/gestor-incidencias/api";
import type { Incident, IncidentFilters, IncidentStatus } from "@/types/incident-manager";

type FetchState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success" };

const NO_FILTERS: IncidentFilters = { status: "", origin: "", branch: "" };

// Listado del gestor de incidencias. Vuelve a pedir la lista cuando cambia un filtro, sin recargar
// la página; los filtros los aplica la API (GET /incidents?status=&origin=&branch=).
export function useIncidents() {
  const [filters, setFilters] = useState<IncidentFilters>(NO_FILTERS);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // Si cambian los filtros antes de que llegue la respuesta, se descarta la anterior.
    let cancelled = false;

    async function load() {
      setFetchState({ status: "loading" });
      try {
        const data = await listIncidents(filters);
        if (cancelled) return;
        setIncidents(data);
        setFetchState({ status: "success" });
      } catch (err) {
        if (cancelled) return;
        setFetchState({
          status: "error",
          message: err instanceof Error ? err.message : "No se pudieron cargar las incidencias.",
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [filters, reloadKey]);

  function updateFilter<K extends keyof IncidentFilters>(key: K, value: IncidentFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function replaceIncident(updated: Incident) {
    setIncidents((prev) => prev.map((incident) => (incident.id === updated.id ? updated : incident)));
  }

  // Cambio de estado optimista: la fila muestra el estado nuevo al momento. Si la API lo rechaza o
  // falla, la fila vuelve a ser exactamente la de antes y se devuelve el mensaje para avisar.
  async function changeStatus(incident: Incident, next: IncidentStatus): Promise<string | null> {
    replaceIncident({ ...incident, status: next });
    try {
      replaceIncident(await updateIncidentStatus(incident.id, next));
      return null;
    } catch (err) {
      replaceIncident(incident);
      return err instanceof Error ? err.message : "No se pudo cambiar el estado.";
    }
  }

  return {
    filters,
    updateFilter,
    clearFilters: () => setFilters(NO_FILTERS),
    hasFilters: Boolean(filters.status || filters.origin || filters.branch),
    incidents,
    fetchState,
    changeStatus,
    reload: () => setReloadKey((key) => key + 1),
  };
}
