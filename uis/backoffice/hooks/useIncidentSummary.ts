import { useEffect, useState } from "react";
import { getIncidentSummary } from "@/lib/gestor-incidencias/api";
import type { IncidentSummary } from "@/types/incident-manager";

type SummaryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; summary: IncidentSummary };

// Métricas del panel (GET /incidents/summary). Se cargan por separado del listado: si fallan,
// solo el bloque del resumen muestra el error.
export function useIncidentSummary() {
  const [state, setState] = useState<SummaryState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const summary = await getIncidentSummary();
        if (!cancelled) setState({ status: "success", summary });
      } catch (err) {
        if (!cancelled) {
          setState({ status: "error", message: err instanceof Error ? err.message : "No se pudo cargar el resumen." });
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return {
    state,
    // "Reintentar" tras un error: vuelve a mostrar la carga.
    retry: () => {
      setState({ status: "loading" });
      setReloadKey((key) => key + 1);
    },
    // Tras un cambio de estado en el listado: actualiza las cifras sin vaciar el bloque.
    refresh: () => setReloadKey((key) => key + 1),
  };
}
