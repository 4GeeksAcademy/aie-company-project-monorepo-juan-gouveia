import { useEffect, useState } from "react";
import { listSuppliers } from "@/lib/proveedores/api";
import type { Supplier, SupplierFilters } from "@/types/supplier";

type FetchState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success" };

const NO_FILTERS: SupplierFilters = { country: "", category: "" };

// Carga los proveedores desde la API y vuelve a pedirlos cuando cambia un filtro,
// sin recargar la página. Los filtros los aplica la API (GET /suppliers?country=&category=).
export function useSuppliers() {
  const [filters, setFilters] = useState<SupplierFilters>(NO_FILTERS);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // Si cambian los filtros antes de que llegue la respuesta, se descarta la anterior.
    let cancelled = false;

    async function load() {
      setFetchState({ status: "loading" });
      try {
        const data = await listSuppliers(filters);
        if (cancelled) return;
        setSuppliers(data);
        setFetchState({ status: "success" });
      } catch (err) {
        if (cancelled) return;
        setFetchState({
          status: "error",
          message: err instanceof Error ? err.message : "Error desconocido",
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [filters, reloadKey]);

  function updateFilter<K extends keyof SupplierFilters>(key: K, value: SupplierFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  // Sustituye una fila con la respuesta de la API (cambio de tarifa o de estado).
  function replaceSupplier(updated: Supplier) {
    setSuppliers((prev) => prev.map((supplier) => (supplier.id === updated.id ? updated : supplier)));
  }

  function reload() {
    setReloadKey((key) => key + 1);
  }

  return {
    filters,
    updateFilter,
    clearFilters: () => setFilters(NO_FILTERS),
    hasFilters: Boolean(filters.country || filters.category),
    suppliers,
    fetchState,
    replaceSupplier,
    reload,
  };
}
