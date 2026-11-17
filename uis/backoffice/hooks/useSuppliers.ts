import { useCallback, useState } from "react";
import { useAsyncData } from "@/hooks/useAsyncData";
import { listSuppliers } from "@/lib/proveedores/api";
import type { Supplier, SupplierFilters } from "@/types/supplier";

const NO_FILTERS: SupplierFilters = { country: "", category: "" };

// Carga los proveedores desde la API y vuelve a pedirlos cuando cambia un filtro,
// sin recargar la página. Los filtros los aplica la API (GET /suppliers?country=&category=).
// Si cambian los filtros antes de que llegue la respuesta, useAsyncData descarta la anterior.
export function useSuppliers() {
  const [filters, setFilters] = useState<SupplierFilters>(NO_FILTERS);
  const load = useCallback(() => listSuppliers(filters), [filters]);
  const { state, reload, setData } = useAsyncData(load, "No se pudieron cargar los proveedores.");

  function updateFilter<K extends keyof SupplierFilters>(key: K, value: SupplierFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  // Sustituye una fila con la respuesta de la API (cambio de tarifa o de estado).
  function replaceSupplier(updated: Supplier) {
    setData((prev) => prev.map((supplier) => (supplier.id === updated.id ? updated : supplier)));
  }

  return {
    filters,
    updateFilter,
    clearFilters: () => setFilters(NO_FILTERS),
    hasFilters: Boolean(filters.country || filters.category),
    suppliers: state.status === "success" ? state.data : [],
    fetchState: state,
    replaceSupplier,
    reload,
  };
}
