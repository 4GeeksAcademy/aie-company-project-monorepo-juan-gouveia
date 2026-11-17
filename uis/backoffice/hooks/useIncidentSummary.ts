import { useAsyncData } from "@/hooks/useAsyncData";
import { getIncidentSummary } from "@/lib/gestor-incidencias/api";

// Métricas del panel (GET /incidents/summary). Se cargan por separado del listado: si fallan,
// solo el bloque del resumen muestra el error.
export function useIncidentSummary() {
  const { state, reload, refresh } = useAsyncData(getIncidentSummary, "No se pudo cargar el resumen.");

  return {
    state,
    // "Reintentar" tras un error: vuelve a mostrar la carga.
    retry: reload,
    // Tras un cambio de estado en el listado: actualiza las cifras sin vaciar el bloque.
    refresh,
  };
}
