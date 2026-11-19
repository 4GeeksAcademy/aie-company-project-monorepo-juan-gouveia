import { useEffect, useRef } from "react";
import { track } from "@/lib/telemetry";
import { changedFilterEvents, type ListId } from "@/lib/telemetry/navigation";

// `list_filter_applied` (plan, §5.3): un evento por filtro cambiado, con las filas que quedan.
// - Espera 500 ms sin cambios (debounce de los filtros de texto, §10) y a que la lista tenga su
//   resultado (`resultCount` null mientras carga, en las listas que filtran en la API);
// - el estado inicial de los filtros no es un cambio.
export const FILTER_DEBOUNCE_MS = 500;

export function useListFilterTelemetry(
  listId: ListId,
  filters: Record<string, string>,
  resultCount: number | null,
  textFilters: readonly string[] = []
) {
  const emitted = useRef<Record<string, string> | null>(null);
  emitted.current ??= filters;
  const key = JSON.stringify(filters);

  useEffect(() => {
    if (resultCount === null) return;
    const current = JSON.parse(key) as Record<string, string>;
    const timer = setTimeout(() => {
      const events = changedFilterEvents(listId, emitted.current ?? current, current, resultCount, textFilters);
      for (const event of events) track("list_filter_applied", event);
      emitted.current = current;
    }, FILTER_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // textFilters es una constante de cada lista.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listId, key, resultCount]);
}
