"use client";

import { useDeferredValue, useMemo, useState } from "react";
import EmptyMessage from "@/components/EmptyMessage";
import LoadingMessage from "@/components/LoadingMessage";
import OrderFilters from "@/components/inventario/OrderFilters";
import OrderHistory from "@/components/inventario/OrderHistory";
import RetryableError from "@/components/RetryableError";
import ShowMoreButton from "@/components/ShowMoreButton";
import { useOrders } from "@/hooks/useOrders";
import { useSession } from "@/hooks/useSession";
import { useListFilterTelemetry } from "@/hooks/useListFilterTelemetry";
import { useLocations } from "@/hooks/useLocations";
import { SHOW_MORE_STEP, useShowMore } from "@/hooks/useShowMore";
import { filterOrders, NO_ORDER_FILTERS, type OrderFilters as Filters } from "@/lib/inventory-orders";

// Historial de órdenes, solo de lectura, con filtros por tipo e ingrediente.
export default function OrdersPanel() {
  const { orders, fetchState, reload } = useOrders();
  // Solo para los nombres de los locales: si el catálogo no carga, el historial muestra el número.
  const { locations } = useLocations();
  const { user } = useSession();
  const [filters, setFilters] = useState<Filters>(NO_ORDER_FILTERS);
  // Mientras se escribe, el campo responde al momento y el filtro se aplica con el texto "diferido":
  // React prioriza la pulsación y recalcula la lista cuando el navegador queda libre.
  const ingredient = useDeferredValue(filters.ingredient);

  // Filtrar ~21 000 órdenes cuesta ~5 ms en escritorio y ~30 ms con la CPU de un móvil (más de un
  // fotograma). Sin useMemo se repetiría en cada render, también al pulsar "Mostrar más", que no cambia
  // ni las órdenes ni los filtros. Solo se recalcula si llegan órdenes nuevas o cambia un filtro.
  const filtered = useMemo(
    () => filterOrders(orders, { kind: filters.kind, ingredient }),
    [orders, filters.kind, ingredient]
  );

  const hasFilters = Boolean(filters.kind || filters.ingredient);

  // Pinta 50 filas y 50 más por clic. Vuelve a 50 al cambiar los filtros, no al recargar.
  const { visible, nextCount, showMore } = useShowMore(filtered.rows.length, `${filters.kind}|${ingredient}`, SHOW_MORE_STEP, {
    listId: "order_history",
    filtersActive: hasFilters,
  });

  // Telemetría: qué filtros se usan (el del ingrediente es texto: solo su longitud).
  useListFilterTelemetry(
    "order_history",
    { kind: filters.kind, ingredient },
    fetchState.status === "success" ? filtered.rows.length : null,
    ["ingredient"]
  );
  function updateFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-4">
      {fetchState.status === "loading" && <LoadingMessage>Cargando el historial...</LoadingMessage>}

      {fetchState.status === "error" && (
        <RetryableError onRetry={reload}>
          {fetchState.message}
        </RetryableError>
      )}

      {fetchState.status === "success" &&
        (orders.length === 0 ? (
          <EmptyMessage>Todavía no hay órdenes registradas.</EmptyMessage>
        ) : (
          <>
            <OrderFilters
              filters={filters}
              onChange={updateFilter}
              onClear={() => setFilters(NO_ORDER_FILTERS)}
              hasFilters={hasFilters}
            />
            <p className="text-sm text-black" aria-live="polite">
              {filtered.rows.length} órdenes: {filtered.entries} entradas y {filtered.exits} salidas
              {hasFilters && " con los filtros aplicados"}.
            </p>
            {filtered.rows.length === 0 ? (
              <EmptyMessage>Ninguna orden coincide con los filtros.</EmptyMessage>
            ) : (
              <>
                <OrderHistory orders={filtered.rows.slice(0, visible)} currentUserId={user?.id ?? null} locations={locations} />
                <ShowMoreButton
                  visible={visible}
                  total={filtered.rows.length}
                  nextCount={nextCount}
                  onShowMore={showMore}
                />
              </>
            )}
          </>
        ))}
    </div>
  );
}
