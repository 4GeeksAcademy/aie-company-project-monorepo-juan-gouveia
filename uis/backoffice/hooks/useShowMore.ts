import { useState } from "react";
import { track } from "@/lib/telemetry";
import type { ListId } from "@/lib/telemetry/navigation";

// Filas que se añaden en cada "Mostrar más".
export const SHOW_MORE_STEP = 50;

// Pinta una lista larga por partes: las primeras `step` filas y `step` más en cada `showMore()`.
// Con miles de filas (21 000 órdenes, 10 000 incidencias), pintarlas todas de golpe bloquea el
// navegador varios segundos; los datos ya están cargados, lo que se difiere es el render.
//
// `resetKey` decide cuándo volver al principio: cuando cambia (otros filtros = otra lista), se vuelve
// a `step` filas. No depende de los datos a propósito: un cambio de estado en una fila sustituye la
// lista entera y no debe plegarla ni hacer perder la posición.
// Telemetría (`list_page_extended`, plan §5.3): con `telemetry`, cada "Mostrar más" emite hasta dónde
// llega la lista, cuántas filas tiene y si hay filtros aplicados.
export interface ShowMoreTelemetry {
  listId: ListId;
  filtersActive: boolean;
}

export function useShowMore(total: number, resetKey: string, step = SHOW_MORE_STEP, telemetry?: ShowMoreTelemetry) {
  const [state, setState] = useState({ key: resetKey, count: step });

  // Ajuste del estado durante el render cuando cambia la clave (patrón recomendado por React en vez
  // de un efecto, que pintaría primero la lista larga y luego la recortaría).
  if (state.key !== resetKey) {
    setState({ key: resetKey, count: step });
  }
  const count = state.key === resetKey ? state.count : step;
  const visible = Math.min(count, total);

  return {
    visible,
    hasMore: visible < total,
    // Cuántas filas añadirá el siguiente clic (menos de `step` al final de la lista).
    nextCount: Math.min(step, total - visible),
    showMore: () => {
      if (telemetry && total > 0) {
        track("list_page_extended", {
          list_id: telemetry.listId,
          visible_rows: Math.min(visible + step, total),
          total_rows: total,
          filters_active: telemetry.filtersActive,
        });
      }
      setState((prev) => ({ key: prev.key, count: prev.count + step }));
    },
  };
}
