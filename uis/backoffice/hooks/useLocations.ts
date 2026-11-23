import { useAsyncData } from "@/hooks/useAsyncData";
import { listLocations } from "@/lib/locations";

// Carga el catálogo de locales desde la API. `reload` vuelve a pedirlo (botón "Reintentar").
export function useLocations() {
  const { state, reload } = useAsyncData(listLocations, "No se pudieron cargar los locales.");

  return {
    locations: state.status === "success" ? state.data : [],
    fetchState: state,
    reload,
  };
}
